<script lang="ts">
    import { RefreshCw, Download, Server, Trash2, AlertTriangle, ShieldAlert, Terminal } from 'lucide-svelte';

    let loadingAction = $state<string | null>(null);
    let logs = $state<string>('');
    let showConfirmDialog = $state<boolean>(false);
    let actionToConfirm = $state<{id: string, name: string, description: string, icon: any} | null>(null);

    const tools = [
        {
            id: 'debug-bundle',
            name: 'Generate Debug Bundle',
            description: 'Collect system logs and configs into a downloadable ZIP',
            icon: Download,
            danger: false,
            action: async () => {
                loadingAction = 'debug-bundle';
                try {
                    // For download, we need to handle it via blob or direct link
                    const res = await fetch('/api/tools?action=debug-bundle', {
                        method: 'POST'
                    });
                    if (res.ok) {
                        const blob = await res.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'debug-bundle.zip';
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        window.URL.revokeObjectURL(url);
                        logs = 'Debug bundle generated and downloaded successfully.\n' + logs;
                    } else {
                        logs = `Failed to generate debug bundle: ${res.statusText}\n` + logs;
                    }
                } catch (e: any) {
                    logs = `Error: ${e.message}\n` + logs;
                } finally {
                    loadingAction = null;
                }
            }
        },
        {
            id: 'backup-partitions',
            name: 'Backup Partitions',
            description: 'Backup critical system partitions',
            icon: Server,
            danger: false
        },
        {
            id: 'config-reset',
            name: 'Reset Rinkhals Configuration',
            description: 'Reset configuration files to default (restarts services)',
            icon: RefreshCw,
            danger: true
        },
        {
            id: 'clean-rinkhals',
            name: 'Clean old Rinkhals',
            description: 'Remove leftover files from previous Rinkhals installations',
            icon: Trash2,
            danger: true
        },
        {
            id: 'uninstall-rinkhals',
            name: 'Uninstall Rinkhals',
            description: 'Completely remove Rinkhals and reboot into factory firmware',
            icon: ShieldAlert,
            danger: true
        }
    ];

    async function executeTool(id: string) {
        loadingAction = id;
        logs = `Executing ${id}...\n` + logs;
        try {
            const res = await fetch(`/api/tools?action=${id}`, {
                method: 'POST'
            });
            const data = await res.json();
            if (data.success) {
                logs = `Success (${id}):\n${data.output}\n` + logs;
            } else {
                logs = `Failed (${id}):\n${data.output || 'Unknown error'}\n` + logs;
            }
        } catch (e: any) {
            logs = `Error (${id}): ${e.message}\n` + logs;
        } finally {
            loadingAction = null;
        }
    }

    function confirmAction(tool: any) {
        if (tool.danger) {
            actionToConfirm = tool;
            showConfirmDialog = true;
        } else {
            if (tool.action) {
                tool.action();
            } else {
                executeTool(tool.id);
            }
        }
    }

    function executeConfirmed() {
        if (actionToConfirm) {
            if (actionToConfirm.action) {
                actionToConfirm.action();
            } else {
                executeTool(actionToConfirm.id);
            }
            showConfirmDialog = false;
            actionToConfirm = null;
        }
    }
</script>

<div class="h-full flex flex-col space-y-6">
    <div>
        <h1 class="text-2xl font-bold mb-2">System Management</h1>
        <p class="text-gray-400">Perform maintenance tasks and system administration operations</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {#each tools as tool}
            <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 flex flex-col justify-between items-start">
                <div class="flex items-start mb-4">
                    <div class="p-3 rounded-lg {tool.danger ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'} mr-4">
                        <svelte:component this={tool.icon} size={24} />
                    </div>
                    <div>
                        <h3 class="font-bold text-lg">{tool.name}</h3>
                        <p class="text-gray-400 text-sm mt-1">{tool.description}</p>
                    </div>
                </div>
                <button 
                    class="ml-auto w-full mt-2 py-2 px-4 rounded-md font-medium transition-colors flex justify-center items-center
                    {tool.danger 
                        ? 'bg-red-600 hover:bg-red-500 text-white' 
                        : 'bg-blue-600 hover:bg-blue-500 text-white'}
                    {loadingAction ? 'opacity-50 cursor-not-allowed' : ''}"
                    disabled={loadingAction !== null}
                    onclick={() => confirmAction(tool)}
                >
                    {#if loadingAction === tool.id}
                        <div class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2"></div>
                        Running...
                    {:else}
                        Execute
                    {/if}
                </button>
            </div>
        {/each}
    </div>

    <!-- Output Logs -->
    <div class="flex-1 mt-6 bg-gray-950 rounded-lg border border-gray-800 flex flex-col min-h-64">
        <div class="px-4 py-2 border-b border-gray-800 flex items-center justify-between bg-gray-900/50 rounded-t-lg">
            <h3 class="font-medium text-sm text-gray-400 flex items-center">
                <Terminal size={16} class="mr-2" /> Action Output
            </h3>
        </div>
        <div class="p-4 flex-1 overflow-y-auto">
            <pre class="font-mono text-sm text-gray-300 whitespace-pre-wrap">{logs || 'No actions executed yet.'}</pre>
        </div>
    </div>
</div>

{#if showConfirmDialog}
    <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div class="flex items-center text-red-400 mb-4">
                <AlertTriangle size={32} class="mr-3" />
                <h2 class="text-2xl font-bold">Dangerous Action</h2>
            </div>
            
            <p class="text-gray-300 mb-2">
                Are you sure you want to execute <strong class="text-white">{actionToConfirm?.name}</strong>?
            </p>
            <p class="text-sm text-gray-400 mb-6 font-medium">
                {actionToConfirm?.description} This action cannot be easily undone.
            </p>

            <div class="flex justify-end space-x-3">
                <button 
                    class="px-4 py-2 rounded font-medium bg-gray-700 hover:bg-gray-600 text-white transition-colors"
                    onclick={() => { showConfirmDialog = false; actionToConfirm = null; }}
                >
                    Cancel
                </button>
                <button 
                    class="px-4 py-2 rounded font-medium bg-red-600 hover:bg-red-500 text-white shadow-lg transition-colors"
                    onclick={executeConfirmed}
                >
                    Yes, Execute
                </button>
            </div>
        </div>
    </div>
{/if}