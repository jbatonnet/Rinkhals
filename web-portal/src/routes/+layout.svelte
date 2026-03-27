<script lang="ts">
	import '../app.css';
	import { LayoutDashboard, FolderOpen, Terminal } from 'lucide-svelte';
	let { children } = $props();
</script>

<div class="flex h-screen bg-gray-900 text-gray-100 font-sans">
	<aside class="w-64 bg-gray-950 border-r border-gray-800 flex flex-col">
		<div class="h-16 flex items-center px-6 border-b border-gray-800">
			<h1 class="text-xl font-bold text-white">Rinkhals Portal</h1>
		</div>
		
		<nav class="flex-1 py-6 px-4 space-y-2">
			<a href="/" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<LayoutDashboard size={20} />
				<span class="font-medium">Dashboard</span>
			</a>
			<a href="/files" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<FolderOpen size={20} />
				<span class="font-medium">Files</span>
			</a>
			<a href="/terminal" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<Terminal size={20} />
				<span class="font-medium">Web Terminal</span>
			</a>
		</nav>
	</aside>

	<main class="flex-1 flex flex-col h-screen overflow-hidden">
		<div class="flex-1 overflow-auto bg-gray-900 p-8">
			{@render children()}
		</div>
	</main>
</div>
