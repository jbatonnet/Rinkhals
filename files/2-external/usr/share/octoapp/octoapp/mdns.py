import threading
import time
import os
import json

import dns.resolver

from octoapp.sentry import Sentry
from .localip import LocalIpHelper

# A helper class to resolve mdns domain names to IP addresses, since the request lib doesn't support
# the mdns lookup.
class MDns:

    # How old a cache entry can be before we try to refresh it.
    # We want to keep the cache fresh, so we don't get stuck with a stale DHCP ip address.
    CacheRefreshTimeSec = 20.0

    # How old a cache entry can be before we stop using it.
    # Allow cache entries to exist for up to 24 hours, so we don't have to do long lookups.
    # The only down side to this is if the DHCP ip is hoping a lot, we might get stale IPs sometimes
    # most DHCP systems don't change IPs often, and most of the time they are sticky.
    # Remember! Since the cache entries persist between restarts, this also makes them live longer.
    MaxCacheTimeSec = 24 * 60.0 * 60.0

    _Instance = None
    _Debug = False

    @staticmethod
    def Init(pluginDataFolderPath):
        MDns._Instance = MDns(pluginDataFolderPath)


    @staticmethod
    def Get():
        return MDns._Instance


    def __init__(self, pluginDataFolderPath):
        # Init our DNS name cache.
        self.Lock = threading.Lock()
        self.CacheFilePath = os.path.join(pluginDataFolderPath, "mDnsCache.json")

        # Try to load past stats from the file. If we fail, just restart.
        self.Cache = None
        self._LoadCacheFile()
        if self.Cache is None:
            self._ResetCacheFile()

        # Now that we support only PY3, this should never fail.
        try:
            # Setup the client
            self.dnsResolver = dns.resolver.Resolver()
            # Use the mdns multicast address
            self.dnsResolver.nameservers = ["224.0.0.251"]
            # Use the mdns port.
            self.dnsResolver.port = 5353
        except Exception as e:
            self.dnsResolver = None
            Sentry.Warn("mDNS", "Failed to create DNS class, local dns resolve is disabled. "+str(e))


    # Given a full url with protocol, hostname, and path, this will look for a local mdns hostname, try to resolve it, and return the full URL again with
    # the localhost name replaced. If no localhost name is found, if the resolve fails, or there's no entry in the cache, None is returned.
    def TryToResolveIfLocalHostnameFound(self, url):

        # Parse the hostname out, be it an IP address, domain name, or other.
        protocolEnd = url.find("://")
        if protocolEnd == -1:
            Sentry.Warn("mDNS", "No protocol found for url "+str(url))
            return None
        protocolEnd += len("://")

        # Look for a port (:) first, since there can be a port and path.
        hostnameEnd = url.find(":", protocolEnd)
        if hostnameEnd == -1:
            # If no port found, look for a path.
            hostnameEnd = url.find("/", protocolEnd)
            if hostnameEnd == -1:
                # If there is no port or path, the full url ends with the domain.
                hostnameEnd = len(url)

        # Parse the hostname.
        hostname = url[protocolEnd:hostnameEnd]
        self.LogDebug("Found hostname "+hostname+" in url "+url)

        # Check if there is a .local hostname. Anything else we will ignore.
        if ".local" not in hostname.lower():
            self.LogDebug("No local domain found in "+url)
            return None

        # If we are here, we have a .local domain we should try to resolve.
        resolveResult = self.TryToGetLocalIp(hostname)

        # If we don't get something back, we failed to resolve.
        if resolveResult is None:
            Sentry.Info("mDNS", "mDNS found a .local domain to resolve, but it failed to resolve. hostname: "+str(hostname) + ", url: "+str(url))
            return None

        # Inject the IP resolved into the url.
        result = url[:protocolEnd] + str(resolveResult) + url[hostnameEnd:]
        self.LogDebug("Local domain resolved and replaced. "+str(url) + " -> " + result)
        return result


    # Returns a string with the local IP if the IP can be found, otherwise, it returns None.
    def TryToGetLocalIp(self, domain):
        domainLower = domain.lower()
        nowSec = time.time()

        # See if we have an entry in our cache.
        with self.Lock:
            if domainLower in self.Cache:
                # We have an entry.
                entry = self.Cache[domainLower]
                deltaSec = nowSec - self.GetUpdatedTimeSecFromEntryDict(entry)

                # Check if we need to update async
                if deltaSec > MDns.CacheRefreshTimeSec:
                    self.LogDebug("Found a cache entry for domain, but it's getting old, kicking off an async update. domain: "+domain)
                    self.TryToUpdateCacheAsync(domain)

                # Check if the entry is too old
                if deltaSec < MDns.MaxCacheTimeSec:
                    self.LogDebug("Using cached entry for domain "+domain)
                    return self.GetIpAddressFromEntryDict(entry)

        # If we get here, we don't have an entry or it's too old, so use the normal lookup.
        self.LogDebug("No cache entry found for domain or it's too old. Doing blocking resolve. "+domain)
        result = self._TryToResolve(domain)
        if result is not None:
            return result

        # If we failed to get a resolved result, try one more time for the cache. If anything is in there, we will use it, since anything is better than nothing.
        self.LogDebug("We didn't use a cached entry and the resolved failed, trying the cache one more time.")
        with self.Lock:
            if domainLower in self.Cache:
                # We have an entry. No matter how old it is, try it.
                self.LogDebug("We didn't use a cached entry and the resolved failed, and we found a cache entry, so we are using it.")
                return self.GetIpAddressFromEntryDict(self.Cache[domainLower])

        self.LogDebug("We didn't use a cached entry and the resolved failed, and no existing cache entry was found.")
        return None

    # Returns a string with the local IP if the IP can be found, otherwise, it returns None.
    def _TryToResolve(self, domain):

        # We have seen that occasionally a first resolve won't work, but future resolves will.
        # For this reason, we do shorter lifetime resolves, but try a few times.
        attempt = 0
        while True:

            # Only allow 3 attempts to successfully resolve.
            attempt += 1
            if attempt > 3:
                Sentry.Info("mDNS", "Failed to resolve mdns for domain "+str(domain))
                # Return none to indicate a failure.
                return None

            # If this isn't the first attempt, delay by 200ms
            if attempt > 1:
                time.sleep(0.2)

            try:
                # If possible, get our local IP address, to make sure we broadcast on the right IP address.
                localAdapterIp = LocalIpHelper.TryToGetLocalIp()
                if localAdapterIp is None or len(localAdapterIp) == 0:
                    localAdapterIp = None
                    self.LogDebug("Failed to get local adapter IP.")
                else:
                    self.LogDebug("Local adapter IP found as "+localAdapterIp+" using this as the adapter to query on.")

                # Since we do caching, we allow the lifetime of the lookup to be longer, so we have a better chance of getting it.
                # Don't allow this to throw, so we don't get nosy exceptions on lookup failures.
                answers = self.dnsResolver.resolve(domain, lifetime=3.0,  raise_on_no_answer=False, source=localAdapterIp)

                # Look get the list of IPs returned from the query. Sometimes, there's a multiples. For example, we have seen if docker is installed
                # there are sometimes 172.x addresses.
                ipList = []
                if answers is not None:
                    for data in answers:
                        # Validate.
                        if data is None or data.address is None or len(data.address) == 0:
                            Sentry.Warn("mDNS", "Dns result had data, but there was no IP address")
                            continue

                        self.LogDebug("Resolver found ip "+data.address+" for local hostname "+domain)
                        ipList.append(data.address)

                # If there are no ips, continue trying.
                if len(ipList) == 0:
                    continue

                # Find which is the primary.
                primaryIp = self.GetSameLanIp(ipList)

                # Always update the cache
                with self.Lock:
                    self.Cache[domain.lower()] = self.CreateCacheEntryDict(primaryIp)

                # Save the cache file.
                # TODO - We could async this, but since this will usually be called in the background as a cache refresh anyways, there's no need.
                self._SaveCacheFile()

                # Return the result.
                return primaryIp

            except dns.resolver.LifetimeTimeout:
                # This happens if no one responds, which is expected if the domain has no one listening.
                pass
            except Exception as e:
                Sentry.Error("mDNS", "Failed to resolve mdns for domain "+str(domain)+" e:"+str(e))

            # If we failed to find anything or it threw, don't return so we try again.


    # Given a list of at least 1 IP, this will always return a string that's an IP. It should be the IP we think
    # is the correct IP address for the same local LAN we are on.
    def GetSameLanIp(self, ipList):
        # If there is just one, return it.
        if len(ipList) == 1:
            self.LogDebug("Only one ip returned in the query, returning it")
            return ipList[0]

        # If there are more than one, try to get our IP and match as much of it as possible.
        # This isn't great, but it works.
        ourIp = LocalIpHelper.TryToGetLocalIp()
        # If we fail to get our IP, just return the local.
        if ourIp is None or len(ourIp) == 0:
            self.LogDebug("Failed to get our local IP, using the first returned result.")
            return ipList[0]

        matches = []
        for ip in ipList:
            matches.append(True)

        # See which IP in our list matches this the best.
        offset = 0
        lastBestMatch = -1
        for c in ourIp:
            # For this current char, check if each ip has it still.
            ipIndex = 0
            for ip in ipList:
                if offset >= len(ip):
                    matches[ipIndex] = False
                elif ip[offset] != c:
                    matches[ipIndex] = False
                ipIndex += 1
            offset += 1

            # Check to see how many IPs still match.
            # If none do,       lastMatchingIpIndex = -1
            # If multiple do,   lastMatchingIpIndex = -2
            # If only one does, lastMatchingIpIndex = ipListIndex
            lastMatchingIpIndex = -1
            currentIndex = 0
            while currentIndex < len(ipList):
                if matches[currentIndex] is True:
                    lastBestMatch = currentIndex
                    if lastMatchingIpIndex == -1:
                        lastMatchingIpIndex = currentIndex
                    else:
                        lastMatchingIpIndex = -2
                currentIndex += 1

            # If -1 no ip matches.
            if lastMatchingIpIndex == -1:
                # If lastBestMatch != -1, that means previous to this round at least two IPs both matched, but as of this round, no IPs do.
                # Example, our IP is `192.168.1.41` and the list contains [`172.17.0.1`, `192.168.1.28`, `192.168.1.12`]. Both of the final two will match up to `192.168.1.` and then both fail in the same round.
                # We will just use one of them to return.
                if lastBestMatch != -1:
                    self.LogDebug(f"There were at least two IPs that matched until this round [{offset}] and then neither did. We are selecting [{lastBestMatch}]")
                    return ipList[lastBestMatch]
                # No IP matched.
                self.LogDebug("All ips returned failed to match at the same time, so we are going with index 0.")
                return ipList[0]
            # If it's > -1, we have one matching left
            if lastMatchingIpIndex > -1:
                self.LogDebug("Most matched IP found as "+str(ipList[lastMatchingIpIndex]))
                return ipList[lastMatchingIpIndex]
            # Else it's -2, keep going.

        # If we get to thw end of the list with multiple matches, just pick one.
        c = 0
        for ip in ipList:
            if matches[c] is True:
                Sentry.Info("mDNS", "MDNS got to end of of the IP string with multiple matches, so we will just return this: "+str(ip))
                return ip
            c += 1

        # If we totally fail, just return the first.
        Sentry.Warn("mDNS", "MDNS got to end of GetSameLanIp without selecting an ip.")
        return ipList[0]


    # Starts a thread to update the domain in the cache async.
    def TryToUpdateCacheAsync(self, domain):
        # Spin off a thread to try to resolve the dns and update the cache.
        workerThread = threading.Thread(target=self.TryToUpdateCacheAsync_Thread, args=(domain,))
        workerThread.start()


    def TryToUpdateCacheAsync_Thread(self, domain):
        # Just use _TryToResolve, which will try to resolve and will update the IP on success.
        self.LogDebug("Starting async update for domain "+domain)
        if self._TryToResolve(domain) is None:
            Sentry.Error("mDNS", "Failed to update mdns cache for domain "+str(domain))


    # Logs if the debug flag is set.
    def LogDebug(self, msg):
        if MDns._Debug:
            Sentry.Info("mDNS", msg)

    # Note, we have to use a dict instead of a class here so that it serializes correctly with
    # the normal json serializer.
    def CreateCacheEntryDict(self, address):
        d = {}
        d["UpdateTimeSec"] = time.time()
        d["IpAddress"] = address
        return d

    def GetUpdatedTimeSecFromEntryDict(self, d):
        # Use a try catch incase there's anything that fails to due parsing of old files or such.
        try:
            return d["UpdateTimeSec"]
        except Exception as e:
            Sentry.Error("mDNS", "Failed to get UpdateTimeSec from cache entry dict. "+str(e))
            self._ResetCacheFile()
            return 0


    def GetIpAddressFromEntryDict(self, d):
        # Use a try catch incase there's anything that fails to due parsing of old files or such.
        try:
            return d["IpAddress"]
        except Exception as e:
            Sentry.Error("mDNS", "Failed to get IpAddress from cache entry dict. "+str(e))
            self._ResetCacheFile()
            return "127.0.0.1"

    def _ResetCacheFile(self):
        Sentry.Info("mDNS", "MDns cache file reset")
        self.Cache = {}

    # Blocks to write the current stats to a file.
    def _SaveCacheFile(self):
        try:
            data = {}
            data['Cache'] = self.Cache
            # pylint: disable=unspecified-encoding
            # encoding only supported in py3
            with open(self.CacheFilePath, 'w') as f:
                json.dump(data, f)

        except Exception as e:
            # On any failure, reset the stats.
            self._ResetCacheFile()
            Sentry.Error("mDNS", "_SaveCacheFile failed "+str(e))


    # Does a blocking call to load any current stats from the file.
    def _LoadCacheFile(self):
        try:
            # First check if there's a file.
            if os.path.exists(self.CacheFilePath) is False:
                # No file means this is most likely the first time run.
                self._ResetCacheFile()
                self._SaveCacheFile()
                return

            # Try to open it and get the key. Any failure will null out the key.
            # pylint: disable=unspecified-encoding
            # encoding only supported in py3
            with open(self.CacheFilePath) as f:
                data = json.load(f)
            self.Cache = data["Cache"]
            Sentry.Info("mDNS", "mDns Cache file loaded. Cached Entries Found: "+str(len(self.Cache)))

        except Exception as e:
            self._ResetCacheFile()
            Sentry.Error("mDNS", "_LoadCacheFile failed "+str(e))

    # Used for testing new logic.
    def Test(self):
        MDns._Debug = True
        expectedLocalIp = "192.168.1.64"
        self.DoTest("https://prusa.local:90/test", "https://"+expectedLocalIp+":90/test")
        self.DoTest("https://prusa.local:90", "https://"+expectedLocalIp+":90")
        self.DoTest("https://invalid.local:90", None) # Fails to find anything
        self.DoTest("https://invalid.local/", None)     # Fails to find anything
        self.DoTest("https://prusa.local", "https://"+expectedLocalIp)
        self.DoTest("http://prusa.com/hello", None)
        self.DoTest("http://127.0.0.1/hello", None)
        self.DoTest("http://127.0.0.1:80/hello", None)
        self.DoTest("http://localhost:80/hello", None)

    def DoTest(self, i, expectedOutput):
        Sentry.Info("mDNS", "~~~~ Starting Test For "+i)
        result = MDns.Get().TryToResolveIfLocalHostnameFound(i)
        if result != expectedOutput:
            raise Exception("Failed mdns test for "+i)
        Sentry.Info("mDNS", "~~~~ Finished Test For "+i)
