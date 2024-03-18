# WrapDB
Custom WrapDB packages

## Notes
Meson has very strict requirements for subprojects. Alliedmodders projects do not have:
1. Separation of interface libraries from the core.
2. Library releases.
3. Meson subproject files.

This means that there is nothing left but to patch the package of the necessary libraries.

WrapDB provides the ability to manage packages and available patches.

## Usage
1. Find the `.wrap` file of the required library in the [releases](https://github.com/alliedmodders-dev/wrapdb/releases).
2. Place the `.wrap` file in the subprojects directory of your project.
3. Declare the dependency (it can be found as the left value in the `provide` section of the `.wrap` file) or install it manually using `meson wrap install <wrap_file_name>`.

Projects using `wrap-git` can be updated using `meson subprojects update <project_name>`.<br>
More information can be found [here](https://mesonbuild.com/Wrap-dependency-system-manual.html).

## Contributing
Open a pull request:
1. Create a `.wrap` file inside the subprojects directory.
2. If a patch is required, then reate it with the same name as the `.wrap` file in `subrojects/packagefiles` directory.
3. Follow the [rules](https://mesonbuild.com/Wrap-best-practices-and-tips.html) set by meson.
