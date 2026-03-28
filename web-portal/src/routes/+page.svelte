<script lang="ts">
	import { onMount } from "svelte";
	import { Box, Video } from "lucide-svelte";
	
	type AppInfo = { id: string; name: string; url?: string; port: string; icon: any; status: string; color: string; };

	let apps = $state<AppInfo[]>([]);
	let loading = $state(true);

	const appBlueprints: Record<string, Partial<AppInfo>> = {
                "25-mainsail": { port: "4408", icon: Box, color: "text-blue-400" },
                "26-fluidd": { port: "4409", icon: Box, color: "text-indigo-400" },
                "30-mjpg-streamer": { port: "8080", icon: Video, color: "text-emerald-400" }
	};

	onMount(async () => {
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
	});
</script>

<svelte:head>
	<title>Dashboard - Rinkhals</title>
</svelte:head>

<div class="space-y-6">
	<h2 class="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
		System Overview
	</h2>

	{#if loading}
		<div class="text-gray-400 animate-pulse">Scanning for running services...</div>
	{:else if apps.length === 0}
		<div class="text-gray-500 italic">No web interfaces are currently active or installed.</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
