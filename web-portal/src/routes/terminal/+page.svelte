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

		terminal.writeln('Connecting to Rinkhals...');
		terminal.writeln('Welcome to the Rinkhals Web Terminal MVP!\r\n');

		// Handle resizing
		const resizeObserver = new ResizeObserver(() => {
			fitAddon.fit();
		});
		resizeObserver.observe(terminalContainer);

		return () => {
			resizeObserver.disconnect();
			terminal.dispose();
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

	<div class="flex items-center space-x-2 text-yellow-500 bg-yellow-500/10 p-4 rounded-lg border border-yellow-500/20">
		<AlertTriangle size={20} />
		<p class="text-sm">This is an MVP mock for the Web Terminal. True integration to the Go backend is in-progress.</p>
	</div>
</div>