/*
 * View model for OctoPrint-TPLinkSmartplug
 *
 * Author: crysxd
 * License: AGPLv3
 */
$(function () {
	function octoAppViewModel(parameters) {
		var self = this;
		self.apps = ko.observableArray();

		self.onDataUpdaterPluginMessage = function (plugin, data) {
			if (plugin == "octoapp.settings") {
				self.apps(data.apps);
			}
		};
	};

	OCTOPRINT_VIEWMODELS.push({
		construct: octoAppViewModel,
		dependencies: ["settingsViewModel"],
		elements: ["#octoapp-list"]
	});
});