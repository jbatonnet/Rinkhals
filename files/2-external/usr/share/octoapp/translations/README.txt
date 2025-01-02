Your plugin's translations will reside here. The provided setup.py supports a
couple of additional commands to make managing your translations easier:

babel_extract
    Extracts any translateable messages (marked with Jinja's `_("...")` or
    JavaScript's `gettext("...")`) and creates the initial `messages.pot` file.
babel_refresh
    Reruns extraction and updates the `messages.pot` file.
babel_new --locale=<locale>
    Creates a new translation folder for locale `<locale>`.
babel_compile
    Compiles the translations into `mo` files, ready to be used within
    OctoPrint.
babel_pack --locale=<locale> [ --author=<author> ]
    Packs the translation for locale `<locale>` up as an installable
    language pack that can be manually installed by your plugin's users. This is
    interesting for languages you can not guarantee to keep up to date yourself
    with each new release of your plugin and have to depend on contributors for.

If you want to bundle translations with your plugin, create a new folder
`octoprint_octoapp/translations`. When that folder exists,
an additional command becomes available:

babel_bundle --locale=<locale>
    Moves the translation for locale `<locale>` to octoprint_octoapp/translations,
    effectively bundling it with your plugin. This is interesting for languages
    you can guarantee to keep up to date yourself with each new release of your
    plugin.
