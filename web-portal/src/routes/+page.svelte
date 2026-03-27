<script lang="ts">
	import { Play, Settings, Webhook, Box, HardDrive } from 'lucide-svelte';

	let apps = [
		{ name: 'Mainsail', url: 'http://<printer_ip>:4408', icon: Box, status: 'Running', color: 'text-blue-400' },
		{ name: 'Fluidd', url: 'http://<printer_ip>:4409', icon: Box, status: 'Running', color: 'text-indigo-400' },
	];
</script>

<svelte:head>
	<title>Dashboard - Rinkhals</title>
</svelte:head>

<div class="space-y-6">
	<h2 class="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
		System Overview
	</h2>

	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
		{#each apps as app}
			<a
				href={app.url}
				target="_blank"
				class="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-gray-500 transition-colors shadow-lg block"
			>
				<div class="flex items-center justify-between mb-4">
					<svelte:component this={app.icon} size={32} class={app.color} />
					<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400">
						{app.status}
					</span>
				</div>
				<h3 class="text-xl font-bold text-white mb-1">{app.name}</h3>
				<p class="text-sm text-gray-400">Launch web interface</p>
			</a>
		{/each}
	</div>
</div>