<script lang="ts">
	import { onMount } from "svelte";
	import "../app.css";
	import { LayoutDashboard, FolderOpen, Terminal, Settings, FileText, ScrollText } from "lucide-svelte";
	let { children } = $props();

	let showPasswordModal = $state(false);
	let newUsername = $state("admin");
	let newPassword = $state("");
	let confirmPassword = $state("");
	let errorMsg = $state("");

	onMount(async () => {
		try {
			const host = import.meta.env.DEV ? "http://localhost:8080" : "";
			const res = await fetch(`${host}/api/auth/status`);
			if (res.ok) {
				const data = await res.json();
				if (data.is_default) {
					showPasswordModal = true;
				}
			}
		} catch (e) {
			console.error("Failed to fetch auth status", e);
		}
	});

	async function changePassword() {
		errorMsg = "";
		if (newPassword.length < 5) {
			errorMsg = "Password must be at least 5 characters.";
			return;
		}
		if (newPassword !== confirmPassword) {
			errorMsg = "Passwords do not match.";
			return;
		}
		try {
			const host = import.meta.env.DEV ? "http://localhost:8080" : "";
			const res = await fetch(`${host}/api/auth/change`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ username: newUsername, password: newPassword })
			});
			if (res.ok) {
				showPasswordModal = false;
				alert("Password changed out of default state. Please log in again using your new credentials. (The screen will refresh)");
				window.location.reload();
			} else {
				errorMsg = "Failed to update password. Server returned an error.";
			}
		} catch (e) {
			errorMsg = "Network error updating password.";
		}
	}
</script>

<div class="flex h-screen bg-gray-900 text-gray-100 font-sans">
	<aside class="w-64 bg-gray-950 border-r border-gray-800 flex flex-col">
		<div class="h-20 flex items-center px-4 border-b border-gray-800 space-x-3">
			<div class="w-12 h-12 rounded-lg bg-gray-900 border border-gray-800 flex items-center justify-center overflow-hidden shrink-0 shadow-inner">
				<img src="/assets/logo.png" alt="Rinkhals Logo" class="w-10 h-10 object-contain drop-shadow-md" />
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
			<a href="/editor" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<FileText size={20} />
				<span class="font-medium">Text Editor</span>
			</a>
                        <a href="/management" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"><Settings size={20} /><span class="font-medium">Manage Rinkhals</span></a>

		</nav>
	</aside>

	<main class="flex-1 flex flex-col h-screen overflow-hidden">
		<div class="flex-1 overflow-auto bg-gray-900 p-8">
			{@render children()}
		</div>
	</main>
</div>

{#if showPasswordModal}
<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
	<div class="bg-gray-900 border border-red-500/50 rounded-xl max-w-md w-full p-6 shadow-2xl relative" onclick={(e) => e.stopPropagation()}>
		<div class="absolute -top-3 -right-3 bg-red-600 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg">Action Required</div>
		<h2 class="text-2xl font-bold text-white mb-2 flex items-center gap-2">
			<Settings class="text-red-400" size={24} /> Security Warning
		</h2>
		<p class="text-gray-300 text-sm mb-6 pb-4 border-b border-gray-800">
			Your Rinkhals Monitor is currently using the default factory credentials (<strong>admin</strong>/<strong>rinkhals</strong>). It is highly insecure to leave this exposed, especially since Rinkhals hosts a raw terminal. Please set a new password.
		</p>
		
		<form class="space-y-4" onsubmit={(e) => { e.preventDefault(); changePassword(); }}>
			<div>
				<label class="block text-sm font-medium text-gray-400 mb-1" for="user">Username</label>
				<input id="user" type="text" bind:value={newUsername} class="w-full bg-gray-800 border-gray-700 text-white rounded focus:ring-emerald-500 focus:border-emerald-500" required />
			</div>
			<div>
				<label class="block text-sm font-medium text-gray-400 mb-1" for="pass">New Password</label>
				<input id="pass" type="password" bind:value={newPassword} class="w-full bg-gray-800 border-gray-700 text-white rounded focus:ring-emerald-500 focus:border-emerald-500" required />
			</div>
			<div>
				<label class="block text-sm font-medium text-gray-400 mb-1" for="pass2">Confirm Password</label>
				<input id="pass2" type="password" bind:value={confirmPassword} class="w-full bg-gray-800 border-gray-700 text-white rounded focus:ring-emerald-500 focus:border-emerald-500" required />
			</div>
			
			{#if errorMsg}
				<p class="text-red-400 text-sm py-2">{errorMsg}</p>
			{/if}
			
			<div class="pt-4 flex justify-end">
				<button type="submit" class="px-5 py-2 flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors shadow-lg shadow-emerald-900/20">
					Save Credentials
				</button>
			</div>
		</form>
	</div>
</div>
{/if}