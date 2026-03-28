const fs = require('fs');
const content = fs.readFileSync('/Users/martin/Development/Rinkhals/web-portal/src/routes/+layout.svelte', 'utf8');
const navInsertion = `
			<a href="/logs" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<ScrollText size={20} />
				<span class="font-medium">System Logs</span>
			</a>
			<a href="/editor" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors">
				<FileText size={20} />
				<span class="font-medium">Text Editor</span>
			</a>
`;

let newContent = content.replace('</nav>', navInsertion + '</nav>');
fs.writeFileSync('/Users/martin/Development/Rinkhals/web-portal/src/routes/+layout.svelte', newContent);
