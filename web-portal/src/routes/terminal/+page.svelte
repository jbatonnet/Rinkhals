<script lang="ts">
	import { onMount } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { Terminal as TerminalIcon, AlertTriangle } from 'lucide-svelte';
	import '@xterm/xterm/css/xterm.css';

	let terminalContainer: HTMLElement;
	let terminal: Terminal;
	let fitAddon: FitAddon;

	onMount(() => {
		terminal = new Terminal({
			cursorBlink: true,
			theme: {
				background: '#111827', // Tailwind gray-900
				foreground: '#f3f4f6', // Tailwind gray-100
			},
			fontFamily: '"Fira Code", monospace',
		});

		fitAddon = new FitAddon();
		terminal.loadAddon(fitAddon);
		terminal.open(terminalContainer);
		fitAddon.fit();

		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		// In dev use localhost:8080 where Go runs, in prod use same host
		const wsHost = import.meta.env.DEV ? 'localhost:8080' : window.location.host;
		const ws = new WebSocket(`${protocol}//${wsHost}/api/terminal`);
		ws.binaryType = 'arraybuffer';

		ws.onopen = () => {
			const dims = { cols: terminal.cols, rows: terminal.rows };
			ws.send(JSON.stringify(dims));
			terminal.focus();
		};

		ws.onmessage = (event) => {
			if (event.data instanceof ArrayBuffer) {
				terminal.write(new Uint8Array(event.data));
			} else {
				terminal.write(event.data);
			}
		};

		terminal.onData((data) => {
			if (ws.readyState === WebSocket.OPEN) {
				// Send as text since server handles text as raw data too if it doesn't parse as JSON
				ws.send(data); 
			}
		});

		terminal.onResize((size) => {
			if (ws.readyState === WebSocket.OPEN) {
				ws.send(JSON.stringify({ cols: size.cols, rows: size.rows }));
			}
		});

		// Handle resizing
		const resizeObserver = new ResizeObserver(() => {
			fitAddon.fit();
		});
		resizeObserver.observe(terminalContainer);

		return () => {
			resizeObserver.disconnect();
			terminal.dispose();
			ws.close();
		};
	});
</script>

<div class="h-full flex flex-col space-y-4">
	<div class="flex items-center space-x-3 mb-2">
		<TerminalIcon size={24} class="text-emerald-400" />
		<h2 class="text-2xl font-bold text-white">Console</h2>
	</div>

	<div class="bg-gray-800 rounded-lg p-4 border border-gray-700 flex-1 relative overflow-hidden shadow-xl">
		<div bind:this={terminalContainer} class="absolute inset-0 p-4"></div>
	</div>
</div>