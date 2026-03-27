<script lang="ts">
	import { Folder, FileText, Search, ArrowUp, Download } from 'lucide-svelte';
	import { onMount } from 'svelte';

	let searchQuery = $state('');
	let currentPath = $state('/');
	let files = $state<any[]>([]);
	let loading = $state(true);
	let error = $state('');

	const apiHost = import.meta.env.DEV ? 'http://localhost:8080' : '';

	async function loadFiles(path: string) {
		loading = true;
		error = '';
		try {
			const res = await fetch(`${apiHost}/api/files?path=${encodeURIComponent(path)}`);
			if (!res.ok) throw new Error(await res.text());
			files = await res.json();
			currentPath = path;
		} catch (err: any) {
			error = err.message;
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadFiles('/');
	});

	function handleItemClick(file: any) {
		if (file.type === 'folder') {
			loadFiles(file.path);
		}
	}

	function handleDownload(e: Event, file: any) {
		e.stopPropagation();
		window.open(`${apiHost}/api/download?path=${encodeURIComponent(file.path)}`, '_blank');
	}

	function goUp() {
		if (currentPath === '/') return;
		const parts = currentPath.split('/').filter(Boolean);
		parts.pop();
		loadFiles('/' + parts.join('/'));
	}

	let filteredFiles = $derived(
		files?.filter(f => f.name.toLowerCase().includes(searchQuery.toLowerCase())) || []
	);
</script>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<h2 class="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
			File Browser
		</h2>
		<div class="relative">
			<Search class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
			<input
				bind:value={searchQuery}
				type="text"
				placeholder="Search files..."
				class="bg-gray-800 text-white rounded-lg pl-10 pr-4 py-2 border border-gray-700 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors shadow-inner"
			/>
		</div>
	</div>

	<div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-lg">
		<div class="bg-gray-900/50 px-6 py-4 border-b border-gray-700 flex items-center justify-between">
			<div class="flex items-center space-x-4">
				<button 
					onclick={goUp}
					disabled={currentPath === '/'}
					class="p-2 -ml-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-lg hover:bg-gray-800"
				>
					<ArrowUp size={20} />
				</button>
				<span class="text-gray-300 font-mono text-sm">{currentPath}</span>
			</div>
		</div>

		<table class="w-full text-left">
			<thead class="bg-gray-900/50 text-gray-400 border-b border-gray-700">
				<tr>
					<th class="px-6 py-4 font-semibold text-sm">Name</th>
					<th class="px-6 py-4 font-semibold text-sm">Size</th>
					<th class="px-6 py-4 font-semibold text-sm hidden sm:table-cell">Modified</th>
					<th class="px-6 py-4 font-semibold text-sm text-right">Actions</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-700">
				{#if loading}
					<tr>
						<td colspan="4" class="px-6 py-8 text-center text-gray-500">Loading files...</td>
					</tr>
				{:else if error}
					<tr>
						<td colspan="4" class="px-6 py-8 text-center text-red-400">Error: {error}</td>
					</tr>
				{:else if filteredFiles.length === 0}
					<tr>
						<td colspan="4" class="px-6 py-8 text-center text-gray-500">No files found.</td>
					</tr>
				{:else}
					{#each filteredFiles as file}
						<tr onclick={() => handleItemClick(file)} class="hover:bg-gray-700/50 transition-colors group cursor-pointer">
							<td class="px-6 py-4">
								<div class="flex items-center space-x-3 text-white">
									{#if file.type === 'folder'}
										<Folder size={20} class="text-blue-400 fill-current" />
									{:else if file.name.endsWith('.log')}
										<FileText size={20} class="text-yellow-400" />
									{:else}
										<FileText size={20} class="text-gray-400" />
									{/if}
									<span class="group-hover:text-emerald-400 transition-colors">{file.name}</span>
								</div>
							</td>
							<td class="px-6 py-4 text-gray-400 text-sm">
								{file.type === 'folder' ? '--' : (file.size / 1024).toFixed(1) + ' KB'}
							</td>
							<td class="px-6 py-4 text-gray-400 text-sm hidden sm:table-cell">{file.modified}</td>
							<td class="px-6 py-4 text-right">
								{#if file.type === 'file'}
									<button 
										onclick={(e) => handleDownload(e, file)}
										class="p-2 text-gray-400 hover:text-emerald-400 hover:bg-emerald-400/10 rounded-lg transition-colors"
										title="Download"
									>
										<Download size={18} />
									</button>
								{/if}
							</td>
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
</div>