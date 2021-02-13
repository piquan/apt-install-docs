# apt-install-docs - Install suggested documentation packages
# Copyright (C) 2021  Joel Ray Holveck
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Usage: apt-install-docs [OPTION]...
Install documentation packages that are suggested by installed packages.

If an installed package has a "suggests" dependency that's not already
met, and that dependency has a package name ending in "-doc", then
install it.

For instance, if binutils is already installed but binutils-doc is not,
apt-install-docs will install it.

      -n, --dry-run      list documentation packages but do not install them
                         (configurable as APT::InstallDocs::DryRun)
      -c, --config-file  as with apt-get
      -o, --option       as with apt-ghet
      -h, --help         display this help and exit
      -v, --version      output version information and exit

"""

import sys
import textwrap

import apt
import apt_pkg

__version__ = "0.0.1"


def find(cache):
    """Update the cache object to install docs.

    This contains the main logic of apt-install-docs: finding which
    documentation packages should be installed.  The cache object
    (an instance of apt.cache.Cache) is updated to install the
    appropriate packages.

    This does not take any action by itself; the cache object's
    commit() method needs to be called.

    """

    # Do all this inside an action group, so we can more efficiently
    # commit installation records at the end.
    with cache.actiongroup():
        # Loop over each installed dependency.
        for pkg in cache:
            if pkg.installed is None:
                continue
            # The package is installed.  Get a Version object for the
            # installed version of that Package; each version of a package
            # can have different dependency lists.
            pkg_version = pkg.versions[pkg.installed]
            for dep in pkg_version.suggests:
                if dep.installed_target_versions:
                    # This dependency is already installed; skip it.
                    continue
                # The dependency is not installed.  The dependency
                # object represents a list, since foo>=2|bar can be
                # satisfied by foo-1, foo-2, or bar-1.
                # Find the Version objects that can satisfy the
                # dependency.
                for dvers in dep.target_versions:
                    # Is it a doc package?
                    # We look for any -doc package that the base package
                    # suggests, rather than one based on the base package's
                    # name.  That's because some packages may have doc
                    # packages that are different than ${pkg}-doc, such
                    # as "augeas-lenses" suggesting "augeas-doc".
                    if dvers.package.shortname.endswith("-doc"):
                        # Found one!
                        # Mark it for installation, marked auto (so
                        # it'll be removed when the parent package is
                        # removed).  Note that we mark the package,
                        # not the specific version.
                        dvers.package.mark_install(from_user=False)

                        
def describe(cache, prompt=True):
    """Describe cache changes to the user.

    This will list the packages that the cache will change.  Optionally,
    it will prompt the user to ask if the changes should be committed.

    This lists the packages as if they will be installed, although
    doesn't verify that the dependency resolution algorithm is
    actually only installing packages.

    The return value is True if the user was prompted and confirmed the
    installation request, or False otherwise.
    """
    if not cache.get_changes():
        print("All documentation packages are installed.")
        return False
    print("The following documentation packages will be installed:")
    pkgstr_nowrap = ' '.join(p.name for p in sorted(cache.get_changes()))
    pkgstr = textwrap.fill(pkgstr_nowrap, break_on_hyphens=False,
                           break_long_words=False,
                           initial_indent='  ', subsequent_indent='  ')
    print(pkgstr)
    if not prompt:
        return False
    print("Do you want to continue? [Y/n] ", end='')
    choice = input().lower()
    if not (choice == '' or choice.startswith('y')):
        print("Abort.")
        return False
    return True


def install(cache):
    """Shorthand for cache.commit"""
    cache.commit(fetch_progress=apt.progress.text.AcquireProgress())

    
def main(argv=sys.argv):
    """Orchestrate a command-line invocation.

    This will run all the steps for a command-line invocation of
    apt-install-docs.
    """
    arguments = apt_pkg.parse_commandline(apt_pkg.config,
                [('h', "help", "help"),
                 ('v', "version", "version"),
                 ('n', "dry-run", "APT::InstallDocs::DryRun"),
                 ('c', "config-file", "", "ConfigFile"),
                 ('o', "option", "", "ArbItem")], argv)
    
    if arguments or apt_pkg.config.find_b("help"):
        print("TODO(joelh)")
        return 0
    elif apt_pkg.config.find_b("version"):
        print("apt-install-docs " + __version__ + """
Copyright (C) 2021  Joel Ray Holveck

License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""")
        return 0

    # Check to see whether we're just printing these, or also installing them.
    dry_run = apt_pkg.config.find_b("APT::InstallDocs::DryRun")
    
    cache = apt.cache.Cache(apt.progress.text.OpProgress())
    cache.open()
    find(cache)
    should_install = describe(cache, prompt=not dry_run)
    if should_install:
        install(cache)

    return 0
