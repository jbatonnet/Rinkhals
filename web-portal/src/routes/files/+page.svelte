<script lang="ts">
    import { Folder, FileText, Search, ArrowUp, Download, Trash2, Edit2, FolderPlus, MoveRight, AlertTriangle } from 'lucide-svelte';
    import { onMount } from 'svelte';

    let searchQuery = $state('');
    let currentPath = $state('/');
    let files = $state<any[]>([]);
    let loading = $state(true);
    let error = $state('');
    let selectedFiles = $state<Set<string>>(new Set());

    // Modals state
    let showDeleteConfirm = $state(false);
    let showRenameModal = $state(false);
    let showMoveModal = $state(false);
    let showNewFolderModal = $state(false);
    
    let modalInput = $state('');
    let modalActionLoading = $state(false);

    const apiHost = import.meta.env.DEV ? 'http://localhost:8080' : '';

    async function loadFiles(path: string) {
        loading = true;
        error = '';
        selectedFiles = new Set();
        try {
            const res = await fetch(`${apiHost}/api/files?path=${encodeURIComponent(path)}`);
            if (!res.ok) throw new Error(await res.text());
            files = await res.json() || [];
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

    function toggleSelection(e: Event, path: string) {
        e.stopPropagation();
        let newSet = new Set(selectedFiles);
        if (newSet.has(path)) newSet.delete(path);
        else newSet.add(path);
        selectedFiles = newSet;
    }

    function toggleAll(e: Event) {
        e.stopPropagation();
        if (selectedFiles.size === filteredFiles.length) {
            selectedFiles = new Set();
        } else {
            selectedFiles = new Set(filteredFiles.map((f: any) => f.path));
        }
    }

    function goUp() {
        if (currentPath === '/') return;
        const parts = currentPath.split('/').filter(Boolean);
        parts.pop();
        loadFiles('/' + parts.join('/'));
    }

    let filteredFiles = $derived(
        files?.filter((f: any) => f.name.toLowerCase().includes(searchQuery.toLowerCase())) || []
    );

    // API calls
    async function fsAction(action: string, targets: string[], destination?: string) {
        modalActionLoading = true;
        try {
            const res = await fetch(`${apiHost}/api/fs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, targets, destination })
            });
            const data = await res.json();
            if (!data.success) {
                alert('Operation failed: ' + (data.errors ? data.errors.join(', ') : 'Unknown error'));
            } else {
                await loadFiles(currentPath);
            }
        } catch (e: any) {
            alert('Request error: ' + e.message);
        } finally {
            modalActionLoading = false;
            closeModals();
        }
    }

    function closeModals() {
        showDeleteConfirm = false;
        showRenameModal = false;
        showMoveModal = false;
        showNewFolderModal = false;
        modalInput = '';
    }

    function promptRename() {
        const selected = Array.from(selectedFiles)[0];
        const file = files.find((f: any) => f.path === selected);
        if (file) {
            modalInput = file.path;
            showRenameModal = true;
        }
    }
</script>

<div class="space-y-4">
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

    <!-- Toolbar -->
    <div class="bg-gray-800 rounded-lg p-3 border border-gray-700 flex items-center justify-between min-h-14">
        <div class="flex items-center space-x-2">
            <button onclick={() => { showNewFolderModal = true; modalInput = currentPath === '/' ? '/NewFolder' : currentPath + '/NewFolder'; }} class="flex items-center px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium transition-colors text-white">
                <FolderPlus size={16} class="mr-2" /> New Folder
            </button>
        </div>
        
        <div class="flex items-center space-x-2">
            {#if selectedFiles.size > 0}
                <span class="text-sm text-gray-400 mr-2">{selectedFiles.size} selected</span>
                <button 
                    onclick={promptRename}
                    disabled={selectedFiles.size !== 1} 
                    class="flex items-center px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:hover:bg-gray-700 text-blue-400 rounded text-sm font-medium transition-colors">
                    <Edit2 size={16} class="mr-2" /> Rename
                </button>
                <button 
                    onclick={() => { showMoveModal = true; modalInput = currentPath === '/' ? '/target_directory' : currentPath; }}
                    class="flex items-center px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-yellow-400 rounded text-sm font-medium transition-colors">
                    <MoveRight size={16} class="mr-2" /> Move
                </button>
                <button 
                    onclick={() => showDeleteConfirm = true}
                    class="flex items-center px-3 py-1.5 bg-red-900/50 hover:bg-red-800 text-red-400 rounded text-sm font-medium transition-colors">
                    <Trash2 size={16} class="mr-2" /> Delete
                </button>
            {/if}
        </div>
    </div>

    <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-lg">
        <div class="bg-gray-900/50 px-6 py-4 border-b border-gray-700 flex items-center">
            <button 
                onclick={goUp}
                disabled={currentPath === '/'}
                class="p-2 -ml-2 mr-4 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-lg hover:bg-gray-800"
            >
                <ArrowUp size={20} />
            </button>
            <span class="text-gray-300 font-mono text-sm">{currentPath}</span>
        </div>

        <table class="w-full text-left">
            <thead class="bg-gray-900/50 text-gray-400 border-b border-gray-700">
                <tr>
                    <th class="px-6 py-4 w-12">
                        <input type="checkbox" 
                            checked={filteredFiles.length > 0 && selectedFiles.size === filteredFiles.length}
                            onclick={toggleAll}
                            class="rounded border-gray-600 text-emerald-500 focus:ring-emerald-500 bg-gray-900 cursor-pointer"
                        />
                    </th>
                    <th class="px-6 py-4 font-semibold text-sm">Name</th>
                    <th class="px-6 py-4 font-semibold text-sm">Size</th>
                    <th class="px-6 py-4 font-semibold text-sm hidden sm:table-cell">Modified</th>
                    <th class="px-6 py-4 font-semibold text-sm text-right">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-700">
                {#if loading}
                    <tr><td colspan="5" class="px-6 py-8 text-center text-gray-500">Loading files...</td></tr>
                {:else if error}
                    <tr><td colspan="5" class="px-6 py-8 text-center text-red-400">Error: {error}</td></tr>
                {:else if filteredFiles.length === 0}
                    <tr><td colspan="5" class="px-6 py-8 text-center text-gray-500">No files found.</td></tr>
                {:else}
                    {#each filteredFiles as file}
                        <tr onclick={() => handleItemClick(file)} class="hover:bg-gray-700/50 transition-colors group cursor-pointer {selectedFiles.has(file.path) ? 'bg-gray-700/30' : ''}">
                            <td class="px-6 py-4" onclick={(e) => e.stopPropagation()}>
                                <input type="checkbox" 
                                    checked={selectedFiles.has(file.path)}
                                    onclick={(e) => toggleSelection(e, file.path)}
                                    class="rounded border-gray-600 text-emerald-500 focus:ring-emerald-500 bg-gray-900 cursor-pointer"
                                />
                            </td>
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
                                    {#if file.isText}
                                        <a 
                                            href="/editor?path={encodeURIComponent(file.path)}" 
                                            class="inline-block p-2 text-gray-400 hover:text-cyan-400 hover:bg-cyan-400/10 rounded-lg transition-colors mr-2"
                                            title="Edit File"
                                        >
                                            <Edit2 size={18} />
                                        </a>
                                    {/if}

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

<!-- Modals -->
{#if showDeleteConfirm}
<div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
    <div class="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
        <div class="flex items-center text-red-400 mb-4">
            <AlertTriangle size={24} class="mr-3" />
            <h2 class="text-xl font-bold text-white">Confirm Deletion</h2>
        </div>
        <p class="text-gray-300 mb-6 font-medium">Are you sure you want to delete {selectedFiles.size} selected item(s)? This cannot be undone.</p>
        <div class="flex justify-end space-x-3">
            <button onclick={closeModals} class="px-4 py-2 rounded font-medium bg-gray-700 hover:bg-gray-600 text-white">Cancel</button>
            <button onclick={() => fsAction('delete', Array.from(selectedFiles))} class="px-4 py-2 rounded font-medium bg-red-600 hover:bg-red-500 text-white flex items-center">
                {#if modalActionLoading}<div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></div>{/if}
                Yes, Delete
            </button>
        </div>
    </div>
</div>
{/if}

{#if showRenameModal}
<div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
    <div class="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
        <h2 class="text-xl font-bold text-white mb-4">Rename Item</h2>
        <input type="text" bind:value={modalInput} class="w-full bg-gray-950 border border-gray-600 rounded px-3 py-2 text-white mb-6 font-mono text-sm focus:outline-none focus:border-blue-500" />
        <div class="flex justify-end space-x-3">
            <button onclick={closeModals} class="px-4 py-2 rounded font-medium bg-gray-700 hover:bg-gray-600 text-white">Cancel</button>
            <button onclick={() => fsAction('rename', Array.from(selectedFiles), modalInput)} class="px-4 py-2 rounded font-medium bg-blue-600 hover:bg-blue-500 text-white flex items-center">
                {#if modalActionLoading}<div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></div>{/if}
                Rename
            </button>
        </div>
    </div>
</div>
{/if}

{#if showMoveModal}
<div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
    <div class="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
        <h2 class="text-xl font-bold text-white mb-4">Move {selectedFiles.size} Item(s)</h2>
        <label for="move_dest" class="block text-sm text-gray-400 mb-1">Destination Directory (absolute path):</label>
        <input id="move_dest" type="text" bind:value={modalInput} class="w-full bg-gray-950 border border-gray-600 rounded px-3 py-2 text-white mb-6 font-mono text-sm focus:outline-none focus:border-yellow-500" />
        <div class="flex justify-end space-x-3">
            <button onclick={closeModals} class="px-4 py-2 rounded font-medium bg-gray-700 hover:bg-gray-600 text-white">Cancel</button>
            <button onclick={() => fsAction('move', Array.from(selectedFiles), modalInput)} class="px-4 py-2 rounded font-medium bg-yellow-600 hover:bg-yellow-500 text-white flex items-center">
                {#if modalActionLoading}<div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></div>{/if}
                Move
            </button>
        </div>
    </div>
</div>
{/if}

{#if showNewFolderModal}
<div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
    <div class="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
        <h2 class="text-xl font-bold text-white mb-4">New Folder</h2>
        <label for="new_folder" class="block text-sm text-gray-400 mb-1">Folder Path:</label>
        <input id="new_folder" type="text" bind:value={modalInput} class="w-full bg-gray-950 border border-gray-600 rounded px-3 py-2 text-white mb-6 font-mono text-sm focus:outline-none focus:border-emerald-500" />
        <div class="flex justify-end space-x-3">
            <button onclick={closeModals} class="px-4 py-2 rounded font-medium bg-gray-700 hover:bg-gray-600 text-white">Cancel</button>
            <button onclick={() => fsAction('mkdir', [], modalInput)} class="px-4 py-2 rounded font-medium bg-emerald-600 hover:bg-emerald-500 text-white flex items-center">
                {#if modalActionLoading}<div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></div>{/if}
                Create
            </button>
        </div>
    </div>
</div>
{/if}