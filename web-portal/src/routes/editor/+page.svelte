<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { Save, FileText, AlertCircle, Loader2 } from 'lucide-svelte';

    let filePath = $state($page.url.searchParams.get("path") || "/opt/rinkhals/start.sh");

    let content = $state('');
    let loading = $state(false);
    let saving = $state(false);
    let message = $state({ text: '', isError: false });

    async function loadFile() {
        loading = true;
        message = { text: '', isError: false };
        try {
            const res = await fetch(`/api/download?path=${encodeURIComponent(filePath)}`);
            if (res.ok) {
                content = await res.text();
            } else {
                message = { text: `Failed to load: ${res.statusText}`, isError: true };
                content = '';
            }
        } catch (e: any) {
            message = { text: `Error: ${e.message}`, isError: true };
            content = '';
        } finally {
            loading = false;
        }
    }

    async function saveFile() {
        saving = true;
        message = { text: '', isError: false };
        try {
            const res = await fetch('/api/saveFile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath, content })
            });

            if (res.ok) {
                message = { text: 'File saved successfully', isError: false };
                setTimeout(() => message.text = '', 3000);
            } else {
                message = { text: `Failed to save: ${res.statusText}`, isError: true };
            }
        } catch (e: any) {
            message = { text: `Error: ${e.message}`, isError: true };
        } finally {
            saving = false;
        }
    }

    onMount(() => {
        loadFile();
    });
</script>

<svelte:head>
    <title>Text Editor - Rinkhals</title>
</svelte:head>

<div class="space-y-6 h-full flex flex-col">
    <div class="flex items-center justify-between">
        <h2 class="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent flex items-center gap-3">
            <FileText size={32} class="text-emerald-400"/>
            Text Editor
        </h2>

        <div class="flex items-center space-x-4">
            {#if message.text}
                <div class="flex items-center text-sm {message.isError ? 'text-red-400' : 'text-emerald-400'}">
                    {#if message.isError}<AlertCircle size={16} class="mr-2"/>{/if}
                    {message.text}
                </div>
            {/if}

            <div class="flex items-center bg-gray-800 rounded-lg p-1 border border-gray-700">
                <input 
                    type="text" 
                    bind:value={filePath} 
                    placeholder="Enter file path..." 
                    class="bg-transparent border-none text-white px-3 py-1.5 focus:outline-none w-64 text-sm"
                    onkeypress={(e) => e.key === 'Enter' && loadFile()}
                />
                <button 
                    onclick={loadFile}
                    disabled={loading}
                    class="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm text-white font-medium transition-colors disabled:opacity-50"
                >
                    Load
                </button>
            </div>

            <button 
                onclick={saveFile}
                disabled={saving || loading || !content}
                class="flex items-center px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 gap-2"
            >
                {#if saving}
                    <Loader2 size={18} class="animate-spin" />
                    Saving...
                {:else}
                    <Save size={18} />
                    Save File
                {/if}
            </button>
        </div>
    </div>

    <div class="flex-1 rounded-xl overflow-hidden border border-gray-700 relative">
        {#if loading}
            <div class="absolute inset-0 bg-gray-900/50 flex flex-col items-center justify-center z-10 backdrop-blur-sm">
                <Loader2 size={48} class="text-emerald-500 animate-spin mb-4" />
                <span class="text-gray-300 font-medium">Loading contents...</span>
            </div>
        {/if}
        
        <textarea
            bind:value={content}
            class="w-full h-full bg-gray-950 text-gray-300 font-mono text-sm p-4 focus:outline-none resize-none"
            placeholder="File content..."
            spellcheck="false"
        ></textarea>
    </div>
</div>