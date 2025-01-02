//
// Logging Helpers
//
var octoapp_debug_log = false; 
function octoapp_log(msg)
{
    if(!octoapp_debug_log)
    {
        return;
    }
    console.log("OctoApp INFO: "+msg)
}
function octoapp_error(msg)
{
    console.log("OctoApp ERROR: "+msg)
}

octoapp_do_load = function()
{
   octoapp_log("Loaded")
};
// Since we use the async script tag, sometimes we are loaded after the dom is ready, sometimes before.
// If so, do the load work now.
if(document.readyState === 'loading')
{
    octoapp_log("Deferring load for DOMContentLoaded")
    document.addEventListener('DOMContentLoaded', octoapp_do_load);
}
else
{
    octoapp_log("Dom is ready, loading now.")
    octoapp_do_load()
}
