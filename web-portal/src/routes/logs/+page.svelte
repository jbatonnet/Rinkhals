<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { Terminal, Play, Square, Loader2 } from 'lucide-svelte';

    let logs = $state<string[]>([]);
    let ws: WebSocket | null = null;
    let autoScroll = $state(true);
    let logContainer: HTMLElement;
    
    let activeLog = $state('/var/log/rinkhals.log');
    const logFiles = [
        { name: "Rinkhals", path: "/useremain/rinkhals/rinkhals.log" },
        { name: "Klipper (gklib)", path: "/useremain/log/gklib.log" },
        { name: "Moonraker", path: "/useremain/home/rinkhals/printer_data/logs/moonraker.log" },
        { name: "GKAPI", path: "/useremain/log/gkapi.log" }
    ];

    function connectWs() {
        if (ws) {
            ws.close();
        }
        logs = [];
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const hostname = typeof window !== 'undefined' ? window.location.host : 'localhost:8080';
        ws = new WebSocket(`${protocol}//${hostname}/api/logstream?path=${encodeURIComponent(activeLog)}`);
        
        ws.onmessage = (event) => {
            logs = [...logs, event.data];
            if (logs.length > 500) logs = logs.slice(logs.length - 500); // keep last 500 lines
            
            if (autoScroll && logContainer) {
                setTimeout(() => {
                    logContainer.scrollTop = logContainer.scrollHeight;
                }, 10);
            }
        };
        
        ws.onerror = () => {
            logs = [...logs, '-- Connection error --'];
        };
        
        ws.onclose = () => {
            logs = [...logs, '-- Connection closed --'];
        };
    }

    onMount(() => {
        connectWs();
    });

    onDestroy(() => {
        if (ws) ws.close();
    });

    function switchLog(path: string) {
        activeLog = path;
        connectWs();
    }
</script>

<svelte:head>
    <title>Log Viewer - Rinkhals</title>
</svelte:head>

<div class="space-y-6 h-full flex flex-col">
    <div class="flex items-center justify-between">
        <h2 class="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            System Logs
        </h2>
        <div class="flex space-x-2">
            {#each logFiles as lf}
                <button 
                    class="px-4 py-2 rounded-lg text-sm font-medium transition-colors {activeLog === lf.path ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 border border-gray-700'}"
                    onclick={() => switchLog(lf.path)}
                >
                    {lf.name}
                </button>
            {/each}
            <button 
                class="px-4 py-2 ml-4 rounded-lg text-sm font-medium border transition-colors {autoScroll ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' : 'bg-gray-800 text-gray-400 border-gray-700'}"
                onclick={() => autoScroll = !autoScroll}
            >
                Auto-scroll {autoScroll ? 'ON' : 'OFF'}
            </button>
        </div>
    </div>

    <div class="flex-1 bg-gray-950 border border-gray-800 rounded-xl p-4 overflow-hidden relative">
        <div class="absolute inset-0 p-4 overflow-y-auto font-mono text-sm text-gray-300 whitespace-pre scroll-smooth" bind:this={logContainer}>
            {#each logs as line}
                <div class="hover:bg-gray-800/50 px-1">{line}</div>
            {/each}
            {#if logs.length === 0}
                <div class="text-gray-600 italic">Waiting for log data...</div>
            {/if}
        </div>
    </div>
</div>