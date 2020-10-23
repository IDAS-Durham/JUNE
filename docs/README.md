# JUNE Documentation

## Infrastructure

This documentation is configured and built using the
[Sphinx documentation tool](https://www.sphinx-doc.org/en/master/) which uses
[reStructuredText format](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html) for writing source files.

The output is a set of inter-linked HTML webpages contained inside
`built_docs/html/`.

## Viewing the built HTML


**To view** the documentation as-is, open ``docs/built_docs/html/index.html``
to display the index page (effective homepage) in a browser, for example
by running from the root repository directory:

```
firefox docs/built_docs/html/index.html &
```

## Updating and rebuilding the HTML

### General build

Generally, to rebuild the documentation so it is up-to-date with the
current state of the `june` codebase, change into the `docs` directory
and run a pair of `make` commands:

```
cd <path to JUNE>/JUNE/docs
make clean
make html
```

which will wipe the built HTML pages under ``built_docs/`` and then
re-build them based on the local state of `june`. Note that a working
environment for running `june` is required (for parsing the codebase)
and some dependencies are also needed, namely:

* [Sphinx](https://www.sphinx-doc.org/en/master/usage/installation.html);
* a Sphinx extension:
  * [``sphinx-pyreverse``](https://pypi.org/project/sphinx-pyreverse/) (for
    the auto-generation of the class and module diagrams).

However, if any classes, methods and/or functions have been removed since
the last build, there will likely be errors thrown by the build process.
This will be indicated via messages to STDERR as the build is attempted
after the `make html` command.

Once the build is complete without errors (possibly there will be many
warnings present but generally these indicate that there is some
non-conformant formatting in a docstring, so are no) the pages can be
viewed as described above.
