<script lang="ts">
	import { Folder, FileText, Search } from 'lucide-svelte';

	let searchQuery = '';
	
	const mockFiles = [
		{ name: 'config.json', type: 'file', size: '2 KB', modified: '2023-11-20' },
		{ name: 'klipper_config', type: 'folder', size: '--', modified: '2023-11-19' },
		{ name: 'moonraker.log', type: 'file', size: '150 KB', modified: 'Just now' },
	];
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
		<table class="w-full text-left">
			<thead class="bg-gray-900/50 text-gray-400 border-b border-gray-700">
				<tr>
					<th class="px-6 py-4 font-semibold text-sm">Name</th>
					<th class="px-6 py-4 font-semibold text-sm">Size</th>
					<th class="px-6 py-4 font-semibold text-sm hidden sm:table-cell">Modified</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-700">
				{#each mockFiles as file}
					<tr class="hover:bg-gray-700/50 transition-colors group cursor-pointer">
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
						<td class="px-6 py-4 text-gray-400 text-sm">{file.size}</td>
						<td class="px-6 py-4 text-gray-400 text-sm hidden sm:table-cell">{file.modified}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>