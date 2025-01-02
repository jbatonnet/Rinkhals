import os
import threading
import hashlib
import random
import string

from octoapp.sentry import Sentry
from octoapp.ostypeidentifier import OsTypeIdentifier

from octoapp.Proto import OsType

# A class to handle getting our UI into common front ends.
class UiInjector():

    # This is how often we will check the state of things.
    # Since our checks are light weight, there's no harm in doing this somewhat frequently.
    # We don't have any other way of detecting file changes right now, so this is our only way.
    c_UpdateCheckIntervalSec = 60

    _Instance = None
    _Debug = False


    @staticmethod
    def Init(repoRoot:str):
        UiInjector._Instance = UiInjector(repoRoot)


    @staticmethod
    def Get():
        return UiInjector._Instance


    def __init__(self, oeRepoRoot:str):
        self.OeRepoRoot = oeRepoRoot
        self.StaticUiJsFilePath = None
        self.StaticUiCssFilePath = None
        self.StaticFileHash = None
        self.WorkerEvent = threading.Event()
        self.WorkerThread = threading.Thread(target=self._Worker)
        self.WorkerThread.start()


    def _Worker(self):
        while True:
            try:
                # Do our update logic before sleeping, so we activate right when the service loads.
                # This function has it's own try except, so it won't throw out.
                self._ExecuteOnce()

                # Now wait on our event handle.
                self.WorkerEvent.wait(UiInjector.c_UpdateCheckIntervalSec)

            except Exception as e:
                Sentry.Exception("UiInjector worker exception.", e)


    # Does the work.
    def _ExecuteOnce(self) -> None:
        try:
            # First, find our static files and update the hash
            # If this fails, it will throw.
            self._FindStaticFilesAndGetHash()

            # Try to find the possible front ends.
            searchRootDir = self.GetParentDirectory(self.OeRepoRoot)

            # If we are running on the sonic pad or the k1, the path we want to search is different.
            osType =OsTypeIdentifier.DetectOsType()
            if osType == OsType.OsType.CrealitySonicPad or osType == OsType.OsType.CrealityK1:
                searchRootDir = "/usr/share/"

            # The list of possible front ends we expect to find.
            # fluidd-pad if found on the sonic pad.
            possibleFrontEndDirs = ["mainsail", "fluidd", "fluidd-pad"]

            # For each possible frontend, try to set it up.
            for frontEnd in possibleFrontEndDirs:
                # Build the possible root.
                htmlStaticRoot = os.path.join(searchRootDir, frontEnd)
                # See if it exists.
                if os.path.exists(htmlStaticRoot):
                    # If so, try to find the html file and inject it if needed.
                    if self._DoInject(htmlStaticRoot):
                        # If successful, make sure our latest js and css files are also there.
                        self._UpdateStaticFilesIntoRootIfNeeded(htmlStaticRoot)
        except Exception as e:
            Sentry.Exception("UiInjector _ExecuteInjectAndUpdate.", e)


    # Ensures we can get paths to the static files in our repo and hashes them.
    def _FindStaticFilesAndGetHash(self):
        expectedRoot = os.path.join(os.path.join(self.OeRepoRoot, "moonraker_octoapp"), "static")
        self.StaticUiJsFilePath = os.path.join(expectedRoot, "octoapp-ui.js")
        self.StaticUiCssFilePath = os.path.join(expectedRoot, "octoapp-ui.css")
        if os.path.exists(self.StaticUiJsFilePath) is False:
            raise Exception("Failed to find static js ui file "+self.StaticUiJsFilePath)
        if os.path.exists(self.StaticUiCssFilePath) is False:
            raise Exception("Failed to find static css ui file "+self.StaticUiCssFilePath)
        # Hash them
        bufferSize = 65536 # 64kb
        sha1 = hashlib.sha1()
        with open(self.StaticUiJsFilePath, 'rb') as f:
            while True:
                data = f.read(bufferSize)
                if not data:
                    break
                sha1.update(data)
        with open(self.StaticUiCssFilePath, 'rb') as f:
            while True:
                data = f.read(bufferSize)
                if not data:
                    break
                sha1.update(data)
        #pylint: disable=consider-using-f-string
        self.StaticFileHash = "{0}".format(sha1.hexdigest())
        self.StaticFileHash = self.StaticFileHash[:10]
        Sentry.Debug("UI Injector", "Static UI Files Hash: "+self.StaticFileHash)


    # Given a known static path, try to inject our UI files.
    # If successful, returns true.
    def _DoInject(self, staticHtmlRootPath) -> bool:
        indexFilePath = os.path.join(staticHtmlRootPath, "index.html")
        if os.path.exists(indexFilePath) is False:
            Sentry.Info("UI Injector", f"Failed to find index.html at {indexFilePath}")
            return False

        # First, see if the inject already exists, and if so, if it needed updating.
        wasFound, wasUpdatedOrAdded = self._UpdateExistingInjections(indexFilePath)

        # If it was not found, inject it now.
        if wasFound is False:
            wasUpdatedOrAdded = True
            if self._InjectIntoHtml(indexFilePath) is False:
                # If the inject fails, we are done.
                return False

        # If the inject was updated or added, we need to update the service worker hash,
        # so the service worker will know the index changed and will refresh it.
        # This is best effort, we don't want to return False if this fails, because then
        # we won't update the static assets.
        if wasUpdatedOrAdded:
            self._UpdateSwHash(staticHtmlRootPath)

        # Success!
        return True


    # Searches the text for our special tag.
    def _FindSpecialJsTagIndex(self, htmlLower) -> int:
        c_jsTagSearch = "src=\"/octoapp/ui."
        return htmlLower.find(c_jsTagSearch)


    # Searches the text for our special tag.
    def _FindSpecialCssTagIndex(self, htmlLower) -> int:
        c_cssTagSearch = "href=\"/octoapp/ui."
        return htmlLower.find(c_cssTagSearch)


    # Tries to find and update existing injections
    # Returns:
    #   bool - If found
    #   bool - If updated
    def _UpdateExistingInjections(self, indexHtmlFilePath):
        try:
            # Read the entire file.
            htmlText = None
            with open(indexHtmlFilePath, 'r', encoding="utf-8") as f:
                htmlText = f.read()

            # Try to find our tags.
            htmlTextLower = htmlText.lower()
            jsTagLocation = self._FindSpecialJsTagIndex(htmlTextLower)
            cssTagLocation = self._FindSpecialCssTagIndex(htmlTextLower)
            if jsTagLocation == -1 or cssTagLocation == -1:
                # Not found, make sure they both aren't there, which is expected.
                if jsTagLocation != -1:
                    Sentry.Error("UI Injector", f"A js tag was found but not a css tag in {indexHtmlFilePath}?")
                if cssTagLocation != -1:
                    Sentry.Error("UI Injector", f"A css tag was found but not a js tag in {indexHtmlFilePath}?")
                return False, False

            # Parse out the hash value.
            jsHashStart = htmlTextLower.find('.', jsTagLocation)
            cssHashStart = htmlTextLower.find('.', cssTagLocation)
            if jsHashStart == -1 or cssHashStart == -1:
                raise Exception("We found js and css tags but couldn't find the hash start?")
            jsHashStart += 1
            cssHashStart += 1

            jsHashEnd = htmlTextLower.find('.', jsHashStart)
            cssHashEnd = htmlTextLower.find('.', cssHashStart)
            if jsHashEnd == -1 or cssHashEnd == -1:
                raise Exception("We found js and css tags but couldn't find the hash end?")

            currentJsHash = htmlText[jsHashStart:jsHashEnd]
            currentCssHash = htmlText[cssHashStart:cssHashEnd]

            # Ensure they are up-to-date
            if self.StaticFileHash == currentJsHash and self.StaticFileHash == currentCssHash:
                Sentry.Debug("UI Injector", "Found existing ui tags and the hash matches the current files.")
                return True, False

            # We need to update the hash tags.
            htmlText = htmlText[:jsHashStart] + self.StaticFileHash + htmlText[jsHashEnd:]
            htmlText = htmlText[:cssHashStart] + self.StaticFileHash + htmlText[cssHashEnd:]

            # Write the file back.
            with open(indexHtmlFilePath, 'w', encoding="utf-8") as f:
                f.write(htmlText)

            Sentry.Info("UI Injector", "Found existing ui tags but the hash didn't match, so we updated the hash.")
            return True, True
        except Exception as e:
            Sentry.Exception("_InjectIntoHtml failed for "+indexHtmlFilePath, e)
        return False, False


    # Assuming there are no injects, this adds them.
    def _InjectIntoHtml(self, indexHtmlFilePath) -> bool:
        try:
            # Read the entire file.
            htmlText = None
            with open(indexHtmlFilePath, 'r', encoding="utf-8") as f:
                htmlText = f.read()

            htmlTextLower = htmlText.lower()
            headEndTag = htmlTextLower.find("</head>")
            if headEndTag == -1:
                Sentry.Error("UI Injector", "Failed to find head tag end in "+indexHtmlFilePath)
                return False

            # Build the tag script.
            # We add some indents to re-create the about correct whitespace.
            # Note that since the update logic needs to find these file names, they can't change!
            # Especially the parts we search for, or there will be multiple tags showing up.
            #    "src=\"/octoapp/ui."
            #    "href=\"/octoapp/ui."
            # The string "octoapp/ui.js?hash=" and "octoapp/ui.css?hash=" are important not to change.
            tags = f"\r\n<!-- OctoApp Injected UI --><script async crossorigin src=\"/octoapp/ui.{self.StaticFileHash}.js\"></script><link crossorigin rel=\"stylesheet\" href=\"/octoapp/ui.{self.StaticFileHash}.css\">\r\n"

            # Inject the tags into the html
            htmlText = htmlText[:headEndTag] + tags + htmlText[headEndTag:]

            # Sanity check we can find our special tags in the result.
            jsIndex = self._FindSpecialJsTagIndex(htmlText)
            cssIndex = self._FindSpecialCssTagIndex(htmlText)
            if jsIndex == -1 or cssIndex == -1:
                Sentry.Error("UI Injector", "Ui injector created new html but the tags weren't found?")
                return False

            # Write the file back.
            with open(indexHtmlFilePath, 'w', encoding="utf-8") as f:
                f.write(htmlText)

            Sentry.Info("UI Injector", "No existing ui tags found, so we added them")
            return True
        except Exception as e:
            Sentry.Exception("_InjectIntoHtml failed for "+indexHtmlFilePath, e)
            return False


    # If it can be found, updates the sw.js file, which is required to get the index refreshed from the service worker.
    def _UpdateSwHash(self, staticHtmlRootPath) -> None:
        # This logic is specific to how workbox works, but both Mainsail and Fluidd use it.
        # Basically workbox is a PWA service worker lib. It handles site caching and a lot of other stuff.
        # The way it handles caching is that it makes a revision number of all of the files it knows of when the project is build,
        # which are stored in the sw.js file. Since the sw.js file is the service worker file, the browser does the work to sync and update
        # the service worker. When the sw.js file changes, the browser will update the service worker. When the service worker gets updated,
        # it has a new hash, and then will get a new copy of the index.
        # As far as  I can tell, the revision number is just random, it doesn't seem to be a hash. (which is weird?) so updating the value
        # to anything new, makes the service worker update the index, and will make it pull again.
        swJsFilePath = os.path.join(staticHtmlRootPath, "sw.js")
        if os.path.exists(swJsFilePath) is False:
            Sentry.Warn("UI Injector", f"Failed to find sw.js at {swJsFilePath}")
            return
        try:
            # Read the entire file.
            swText = None
            with open(swJsFilePath, 'r', encoding="utf-8") as f:
                swText = f.read()

            # Find and parse out the current index hash
            # There might be more than one index.html strings in the file.
            # Our is usually at the end, so we look backwards.
            # Note the text can look like
            #   {url:"index.html",revision:"10e9298b3a0e61eee4baa12f5922ee80"}
            #   OR
            #   {"url":"index.html","revision":"10e9298b3a0e61eee4baa12f5922ee80"}
            swTextLower = swText.lower()
            indexHtmlStrPos = len(swTextLower)
            revisionStart = None
            revisionEnd = None
            while True:
                # We know the file will be minimized, so there will be no white space.
                indexHtmlStrPos = swTextLower.rfind("\"url\":\"index.html\"", 0, indexHtmlStrPos)
                if indexHtmlStrPos == -1:
                    # Check without quotes.
                    indexHtmlStrPos = swTextLower.rfind("url:\"index.html\"", 0, indexHtmlStrPos)
                    if indexHtmlStrPos == -1:
                        Sentry.Warn("UI Injector", "_UpdateSwHash failed to find the right index.html")
                        return
                # The url can be first or last in the json object, so we need to find the object.
                jsonObjectStart = swTextLower.rfind('{', 0, indexHtmlStrPos)
                jsonObjectEnd   = swTextLower.find('}', indexHtmlStrPos)
                if jsonObjectStart == -1 or jsonObjectEnd == -1:
                    # Try to find a different index.html string.
                    continue
                # Now find the revision, which must best in the object.
                revisionJsonKeySearch = "\"revision\":\""
                revisionStart = swTextLower.find(revisionJsonKeySearch, jsonObjectStart)
                if revisionStart == -1:
                    # Check without quotes.
                    revisionJsonKeySearch = "revision:\""
                    revisionStart = swTextLower.find(revisionJsonKeySearch, jsonObjectStart)
                    if revisionStart == -1:
                        # Try to find a different index.html string.
                        continue
                revisionStart += len(revisionJsonKeySearch)
                revisionEnd = swTextLower.find('"', revisionStart)
                if revisionEnd == -1:
                    # Try to find a different index.html string.
                    Sentry.Warn("UI Injector", "_UpdateSwHash failed to find revisionEnd json object.")
                    continue
                # Success!
                break

            # Sanity check we found something
            if revisionStart is None or revisionEnd is None:
                Sentry.Warn("UI Injector", "_UpdateSwHash broke the while loop with no revision start or end?")
                return

            # Parse the current revision.
            currentRevision = swText[revisionStart:revisionEnd]
            newRevision = ''.join(random.choices(string.ascii_lowercase + string.digits, k=len(currentRevision)))
            Sentry.Info("UI Injector", f"Updating the sw.js index.html revision [{currentRevision}] -> [{newRevision}]")

            # Update it
            swText = swText[:revisionStart] + newRevision + swText[revisionEnd:]

            # Write the file back.
            with open(swJsFilePath, 'w', encoding="utf-8") as f:
                f.write(swText)

            Sentry.Info("UI Injector", f"Sw.js [{swJsFilePath}] updated.")
        except Exception as e:
            Sentry.Exception("_UpdateSwHash failed for "+staticHtmlRootPath, e)


    # Copies our static files into the html root, where they are expected to be.
    def _UpdateStaticFilesIntoRootIfNeeded(self, staticHtmlRootPath):
        try:
            # Ensure the dir exists.
            oeStaticFileRoot = os.path.join(staticHtmlRootPath, "octoapp")
            if os.path.exists(oeStaticFileRoot) is False:
                os.makedirs(oeStaticFileRoot)

            # Figure out the current file names.
            jsStaticFileName = f"ui.{self.StaticFileHash}.js"
            cssStaticFileName = f"ui.{self.StaticFileHash}.css"
            jsStaticFilePath = os.path.join(oeStaticFileRoot, jsStaticFileName)
            cssStaticFilePath = os.path.join(oeStaticFileRoot, cssStaticFileName)

            # Ensure the js file exists.
            if os.path.exists(jsStaticFilePath) is False:
                with open(self.StaticUiJsFilePath, 'r', encoding="utf-8") as fr:
                    with open(jsStaticFilePath, 'w', encoding="utf-8") as fw:
                        fw.write(fr.read())

            # Ensure the css file exists.
            if os.path.exists(cssStaticFilePath) is False:
                with open(self.StaticUiCssFilePath, 'r', encoding="utf-8") as fr:
                    with open(cssStaticFilePath, 'w', encoding="utf-8") as fw:
                        fw.write(fr.read())

            # Cleanup all older files.
            for f in os.listdir(oeStaticFileRoot):
                if f != jsStaticFileName and f != cssStaticFileName:
                    os.remove(os.path.join(oeStaticFileRoot, f))
        except Exception as e:
            Sentry.Exception("_UpdateStaticFilesIntoRootIfNeeded failed for "+staticHtmlRootPath, e)


    # Returns the parent directory of the passed directory or file path.
    def GetParentDirectory(self, path):
        return os.path.abspath(os.path.join(path, os.pardir))
