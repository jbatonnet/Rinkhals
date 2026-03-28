<script lang="ts">
    import { RefreshCw, Download, Server, Trash2, AlertTriangle, ShieldAlert, Terminal, Lock } from 'lucide-svelte';

    let loadingAction = $state<string | null>(null);
    let logs = $state<string>('');
    let showConfirmDialog = $state<boolean>(false);
    let actionToConfirm = $state<{id: string, name: string, description: string, icon: any} | null>(null);
    
    // Password change state
    let isChangingPassword = $state(false);
    let authSaving = $state(false);
    let p_username = $state('admin');
    let p_current = $state('');
    let p_new = $state('');
    let p_confirm = $state('');
    let p_error = $state('');
    let p_success = $state('');

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

    async function changePassword() {
        p_error = "";
        p_success = "";
        if (!p_current) {
            p_error = "Current password is required to authorize the change.";
            return;
        }
        if (p_new.length < 5) {
            p_error = "New password must be at least 5 characters.";
            return;
        }
        if (p_new !== p_confirm) {
            p_error = "New passwords do not match.";
            return;
        }
        authSaving = true;
        try {
            // Test current auth first using the /api/auth/status trick with basic auth
            const creds = btoa(`${p_username}:${p_current}`);
            const host = import.meta.env.DEV ? "http://localhost:8080" : "";
            const testRes = await fetch(`${host}/api/auth/status`, {
                headers: { 'Authorization': `Basic ${creds}` }
            });
            
            if (!testRes.ok) {
                p_error = "Current username/password is incorrect.";
                authSaving = false;
                return;
            }

            // If auth is valid, proceed to change
            const res = await fetch(`${host}/api/auth/change`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    'Authorization': `Basic ${creds}` 
                },
                body: JSON.stringify({ username: p_username, password: p_new })
            });

            if (res.ok) {
                p_success = "Password updated successfully. You will need to log in again using your new credentials. Refreshing page in 3 seconds...";
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
            } else {
                p_error = "Failed to update password.";
            }
        } catch (e) {
            p_error = "Network or server error updating credentials.";
        }
        authSaving = false;
    }
</script>

<div class="h-full flex flex-col space-y-6">
    <div>
        <h1 class="text-2xl font-bold mb-2">System Management</h1>
        <p class="text-gray-400">Perform maintenance tasks and system administration operations</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {#each tools as tool}
            {@const Icon = tool.icon}
            <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 flex flex-col justify-between items-start">
                <div class="flex items-start mb-4">
                    <div class="p-3 rounded-lg {tool.danger ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'} mr-4">
                        <Icon size={24} />
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

        <!-- Password Change Card -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700 flex flex-col justify-between hover:border-gray-600 transition-colors shadow-lg">
            <div>
                <div class="flex items-start mb-4">
                    <div class="p-3 rounded-lg bg-emerald-900/30 text-emerald-400 mr-4">
                        <Lock size={24} />
                    </div>
                    <div>
                        <h3 class="text-lg font-bold text-white mb-1">Web Authentication</h3>
                        <p class="text-gray-400 text-sm">Change the username and password used to access the Rinkhals Web Portal.</p>
                    </div>
                </div>
            </div>
            <button 
                class="w-full mt-4 px-4 py-2 rounded-lg font-medium transition-colors bg-gray-700 hover:bg-gray-600 text-white"
                onclick={() => isChangingPassword = true}
            >
                Change Credentials
            </button>
        </div>
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

{#if isChangingPassword}
    <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-gray-800 border border-gray-700 rounded-xl max-w-md w-full p-6 shadow-2xl relative">
            <h2 class="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                <Lock class="text-emerald-400" size={24} /> Change Credentials
            </h2>
            <p class="text-gray-400 text-sm mb-6 pb-4 border-b border-gray-700">
                Update the authentication required for this web interface.
            </p>
            
            <form onsubmit={(e) => { e.preventDefault(); changePassword(); }} class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-1" for="p_user">Username</label>
                    <input id="p_user" type="text" bind:value={p_username} class="w-full bg-gray-900 border-gray-700 text-white rounded focus:ring-emerald-500 focus:border-emerald-500" required />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-1" for="p_curr">Current Password</label>
                    <input id="p_curr" type="password" bind:value={p_current} class="w-full bg-gray-900 border-gray-700 text-white rounded focus:ring-emerald-500 focus:border-emerald-500" required />
                </div>
                <div class="pt-2">
                    <label class="block text-sm font-medium text-gray-400 mb-1" for="p_new">New Password</label>
                    <input id="p_new" type="password" bind:value={p_new} class="w-full bg-gray-900 border-gray-700 text-white rounded focus:ring-emerald-500 focus:border-emerald-500" required />
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-1" for="p_conf">Confirm New Password</label>
                    <input id="p_conf" type="password" bind:value={p_confirm} class="w-full bg-gray-900 border-gray-700 text-white rounded focus:ring-emerald-500 focus:border-emerald-500" required />
                </div>
                
                {#if p_error}
                    <p class="text-red-400 text-sm bg-red-900/20 p-3 rounded">{p_error}</p>
                {/if}
                {#if p_success}
                    <p class="text-emerald-400 text-sm bg-emerald-900/20 p-3 rounded">{p_success}</p>
                {/if}
                
                <div class="flex justify-end space-x-3 pt-4">
                    <button 
                        type="button"
                        class="px-4 py-2 rounded font-medium bg-gray-700 hover:bg-gray-600 text-white transition-colors"
                        onclick={() => { isChangingPassword = false; p_error = ''; p_success = ''; p_current = ''; p_new = ''; p_confirm = ''; }}
                        disabled={authSaving || p_success !== ''}
                    >
                        Cancel
                    </button>
                    <button 
                        type="submit"
                        class="px-4 py-2 rounded font-medium bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg transition-colors flex items-center justify-center disabled:opacity-50 {authSaving ? 'animate-pulse' : ''}"
                        disabled={authSaving || p_success !== ''}
                    >
                        {authSaving ? "Saving..." : "Save Credentials"}
                    </button>
                </div>
            </form>
        </div>
    </div>
{/if}