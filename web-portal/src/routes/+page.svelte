<script lang="ts">
	import { onMount, onDestroy } from "svelte";
	import { Box, Video, MonitorPlay, Activity, Cpu, HardDrive, Printer, Thermometer } from "lucide-svelte";

	type AppInfo = { id: string; name: string; url?: string; port: string; icon: any; status: string; color: string; };

	let apps = $state<AppInfo[]>([]);
	let loading = $state(true);
	let metrics = $state<{uptime: string, cpuLoad: string, memUsage: number, diskUsage: number} | null>(null);
	let printer = $state<{state: string, bedTemp: number, hotendTemp: number} | null>(null);

	const appBlueprints: Record<string, Partial<AppInfo>> = {
		"25-mainsail": { port: "4409", icon: Box, color: "text-blue-400" },
		"26-fluidd": { port: "4408", icon: Box, color: "text-indigo-400" },
		"30-mjpg-streamer": { port: "8080", icon: Video, color: "text-emerald-400" },
		"50-remote-display": { port: "5800", icon: MonitorPlay, color: "text-purple-400" }
	};

	let pollingInterval: any;

	const fetchData = async () => {
		const hostname = window.location.hostname;
		const protocol = window.location.protocol;
		
		try {
			const res = await fetch('/api/services');
			if (res.ok) {
				const services: {id: string, name: string, status: string}[] = await res.json();
				
				apps = services
					.filter(s => appBlueprints[s.id])
					.map(s => {
						const bp = appBlueprints[s.id]!;
						return {
							id: s.id,
							name: s.name,
							url: `${protocol}//${hostname}:${bp.port}`,
							port: bp.port || "",
							icon: bp.icon,
							status: s.status,
							color: bp.color || "text-gray-400"
						};
					});
			}
		} catch (e) {
			console.error("Failed to load services", e);
		} finally {
			loading = false;
		}

		try {
			const res = await fetch('/api/metrics');
			if (res.ok) {
				metrics = await res.json();
			}
		} catch (e) {
			console.error("Failed to load metrics", e);
		}

		try {
			const res = await fetch(`${protocol}//${hostname}:7125/printer/objects/query?webhooks&extruder=temperature&heater_bed=temperature&print_stats`);
			if (res.ok) {
				const data = await res.json();
				printer = {
					state: data?.result?.status?.print_stats?.state || "unknown",
					bedTemp: data?.result?.status?.heater_bed?.temperature || 0,
					hotendTemp: data?.result?.status?.extruder?.temperature || 0
				};
			} else {
				printer = null;
			}
		} catch (e) {
			printer = null;
		}
	};

	onMount(() => {
		fetchData();
		pollingInterval = setInterval(fetchData, 5000);
	});

	onDestroy(() => {
		if (pollingInterval) clearInterval(pollingInterval);
	});
</script>

<svelte:head>
	<title>Dashboard - Rinkhals</title>
</svelte:head>

<div class="space-y-6 flex flex-col min-h-[calc(100vh-8rem)]">
	<div class="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
		<h2 class="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
			System Overview
		</h2>
		
		<div class="flex flex-wrap items-center gap-4 text-sm text-gray-400 bg-gray-800/50 px-4 py-3 rounded-xl border border-gray-700/50 shadow-inner">
			{#if metrics}
				<div class="flex items-center gap-2" title="CPU Load">
					<Activity size={18} class="text-cyan-400" /> {metrics.cpuLoad}
				</div>
				<div class="flex items-center gap-2" title="Memory Usage">
					<Cpu size={18} class="text-indigo-400" /> {metrics.memUsage}%
				</div>
				<div class="flex items-center gap-2" title="Storage Usage">
					<HardDrive size={18} class="text-purple-400" /> {metrics.diskUsage}%
				</div>
			{:else}
				<div class="animate-pulse">Loading core stats...</div>
			{/if}
			
			<div class="hidden sm:block w-px h-5 bg-gray-700 mx-2"></div>
			
			{#if printer}
				<div class="flex items-center gap-2 font-medium {printer.state === 'printing' ? 'text-emerald-400' : 'text-gray-300'}" title="Printer State">
					<Printer size={18} class={printer.state === 'printing' ? 'animate-pulse' : ''} /> 
					{printer.state.toUpperCase()}
				</div>
				<div class="flex items-center gap-2" title="Hotend / Bed Temperatures">
					<Thermometer size={18} class="text-orange-400" /> 
					{printer.hotendTemp.toFixed(1)}° / {printer.bedTemp.toFixed(1)}°
				</div>
			{:else}
				<div class="flex items-center gap-2 text-gray-500" title="Moonraker Offline">
					<Printer size={18} /> Offline
				</div>
			{/if}
		</div>
	</div>

	{#if loading}
		<div class="text-gray-400 animate-pulse mt-8">Scanning for running services...</div>
	{:else if apps.length === 0}
		<div class="text-gray-500 italic mt-8">No web interfaces are currently active or installed.</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-4">
			{#each apps as app}
				{@const Icon = app.icon}
				{@const isRunning = app.status === "Running"}
				<a 
					href={isRunning ? app.url : "#"} 
					target={isRunning ? "_blank" : undefined}
					class="rounded-xl p-6 border transition-all duration-200 block {isRunning ? 'bg-gray-800 border-gray-700 hover:border-gray-500 shadow-lg' : 'bg-gray-900 border-gray-800/50 opacity-50 cursor-not-allowed shadow-none grayscale'}"
					onclick={(e) => { if (!isRunning) e.preventDefault(); }}
				>
					<div class="flex items-center justify-between mb-4">
						<Icon size={32} class={isRunning ? app.color : 'text-gray-500'} />
						<span class="px-2.5 py-1 text-xs font-semibold rounded-full {isRunning ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}">
							{app.status}
						</span>
					</div>
					<h3 class="text-xl font-bold {isRunning ? 'text-white' : 'text-gray-500'} mb-1">{app.name}</h3>
					<p class="text-sm {isRunning ? 'text-gray-400' : 'text-gray-600'}">
						{isRunning ? 'Launch web interface' : 'Service is currently stopped'}
					</p>
				</a>
			{/each}
		</div>
	{/if}
</div>
