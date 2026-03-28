<script lang="ts">
	import "../app.css";
	import { LayoutDashboard, FolderOpen, Terminal, Settings , FileText, ScrollText } from "lucide-svelte";
	let { children } = $props();
</script>

<div class="flex h-screen bg-gray-900 text-gray-100 font-sans">
	<aside class="w-64 bg-gray-950 border-r border-gray-800 flex flex-col">
		<div class="h-20 flex items-center px-4 border-b border-gray-800 space-x-3">
			<div class="w-12 h-12 rounded-lg bg-gray-900 border border-gray-800 flex items-center justify-center overflow-hidden shrink-0 shadow-inner">
				<img src="/assets/snake-grid.webp" alt="Rinkhals Logo" class="w-10 h-10 object-contain drop-shadow-md" />
			</div>
			<h1 class="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">Rinkhals</h1>
		</div>

		<nav class="flex-1 py-6 px-4 space-y-2">
			<a href="/" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<LayoutDashboard size={20} />
				<span class="font-medium">Dashboard</span>
			</a>			<a href="/files" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<FolderOpen size={20} />
				<span class="font-medium">File Browser</span>
			</a>			<a href="/logs" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<ScrollText size={20} />
				<span class="font-medium">System Logs</span>
			</a>
			<a href="/terminal" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"><Terminal size={20} /><span class="font-medium">Terminal</span></a>
			<a href="/management" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"><Settings size={20} /><span class="font-medium">Machine Settings</span></a>
			<a href="/editor" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<FileText size={20} />
				<span class="font-medium">Text Editor</span>
			</a>
		</nav>
	</aside>

	<main class="flex-1 flex flex-col h-screen overflow-hidden">
		<div class="flex-1 overflow-auto bg-gray-900 p-8">
			{@render children()}
		</div>
	</main>
</div>