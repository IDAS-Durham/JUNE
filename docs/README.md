# JUNE Documentation

*Note*: all references to directories here are assuming the current working
directory is `docs`, so you may need to run
`cd <path to JUNE>/JUNE/docs` or similar first.


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

```console
$ cd <path to JUNE>/JUNE/docs
$ make clean
$ make html
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
after the `make html` command. In this case, see the section below for how
to manage updated classes, methods and/or functions so that the build can
proceed without error.

Once the build is complete without errors (possibly there will be many
warnings present but generally these indicate that there is some
non-conformant formatting in a docstring, so are no) the pages can be
viewed as described above.

### Building after additions or removals to the API

These are the steps to follow so the build progresses without error after
API changes.

There is a Pull Request (`IDAS-Durham/JUNE` `#401`) which can serve as a
template for changes that are required to do so. Commits from it are
referenced for guidance.

1. Determine what has been added or removed from the API since the last
   build. To do this, for now, I recommend the following procedures which
   I used, but going forward you may want to write a script that returns
   any such changes to make or even makes them in-place.

   * Get the **current modules**. You can get them via inspection on the
     `june` module e.g. like this:

     ```python
     import june
     import pkgutil
     module=june
     for submodule in pkgutil.walk_packages(
             module.__path__, prefix=module.__name__ + '.'):
         print(submodule.name)
     ```

     From there you can see all of the modules. Cross reference with those
     already listed in ``source/modules.rst`` to see what needs to be added
     or removed.

   * Get the **current classes**. You could use a small script for this,
     similar to the above, but in this case I found it easy enough to just
     do a `grep` on the `class` reserved word:

     ```console
     $ cd ../june
     $ git grep "class "
     ```

     This gives a view of all the classes in the codebase. Cross reference
     those with the ones already listed under ``source/classes.rst``
     to determine what needs to be added or removed.

   * Get the **current functions**. You can get them via inspection on the
     `june` module e.g. like so:

     ```python
     import june
     import inspect
     import pprint
     all_funcs = []
     for submodule in dir(june):
         functions = inspect.getmembers(
             getattr(june, submodule), inspect.isfunction)
         all_funcs.extend(
             [submodule + "." + func[0] for func in functions])
         pprint.pprint(all_funcs)
     ```

     This will show all of the functions in `june`, but is somewhat
     polluted with some Python module, e.g. `yaml` and `os`, functions, e.g.
     ``yaml.parse`` and ``os.popen``, as well as some methods (i.e.
     functions attached to classes). Ignore those and pick out the `june`
     functions. (Note that any double-underscore methods cannot be
     included in the functions listing as they will break the Sphinx build,
     with an obscure error, at least as far as I saw for my environment
     and Sphinx version, etc.).

     Cross reference with those already listed in ``source/functions.rst``
     to see what needs to be added or removed.

2. Update the following files to add any new objects and remove any old
   ones, based on the results determined in (1):

   * ``source/modules.rst``: modules;
   * ``source/classes.rst``: classes and their methods;
   * ``source/functions.rst``: functions that are not methods.

   Note that new headers may need to be added to organise the various
   objects in each file appropriately.

   * Objects should be added in the same form as the other objects in these
     files (`module.submodule.class` etc.) under the appropriate heading.
     See [this commit as an example](https://github.com/IDAS-Durham/JUNE/pull/401/commits/3ab378e6cefc31102f6dd2ab861ba44d9de423ab)).

   * Objects can be removed by commenting them out by putting `.. ` before
     the object reference, as in
     [this commit](https://github.com/IDAS-Durham/JUNE/pull/401/commits/b61e091c95f63678716016d0b4b9ddb71eb8fbea),
     or by removing the reference completely, as per
     [this commit](https://github.com/IDAS-Durham/JUNE/pull/401/commits/b1abcc7c6cb1ef373e7854d70ae63afbaf1bf96d).

     (I find it was helpful to comment out the old references first and
     then after double-checking remove them completely, hence the two
     commits.)

3. Tidy up the listings in ``source/{modules, classes, functions}.rst``,
   if it seems necessary:

   * create new headings to account for new categories;
   * create new sub-headings to split up long sections into smaller
     sub-section lists;
   * move objects or sub-sections around as appropriate,
   * etc.

   An example of tidying up the listings in this manner is the set of
   changes made to ``source/{modules, classes, functions}.rst`` (only) in
   [this commit](https://github.com/IDAS-Durham/JUNE/pull/401/commits/1e065943ba54cb1bcd2aa1c6709b45380a646eab).

4. Update the ``source/component_diagrams.rst`` to catalogue all current
   modules, adding any new ones and deleting references to old ones,
   as determined in (1).

   If a module is particularly complicated, such that the diagrams are
   quite complex to apprehend as a whole, add sub-sections for the
   individual sub-modules to break the complex diagram into many simpler
   and smaller ones.

   Every module catalogued should be added in the same format as the others,
   namely (using the `geography` module as an example):

   ```rst
   Geography
   ^^^^^^^^^

   Classes
   """""""

   .. uml:: june.geography
       :classes:


   Modules
   """""""

   .. uml:: june.geography
       :packages:

   ```

   Note that in a small number of cases the Sphinx build complains and errors
   on the addition of certain module class and/or module diagrams, for some
   reason that was obscure in the error message and I do not have time to
   investigate (but I suspect due to the diagrams being singular). In these
   cases, just remove the culprit references from
   ``source/component_diagrams.rst``.

   An example of doing this step is the set of changes made to
   ``source/component_diagrams.rst`` in
   [this commit](https://github.com/IDAS-Durham/JUNE/pull/401/commits/1e065943ba54cb1bcd2aa1c6709b45380a646eab).

5. Delete the two directories containing all of the object stubs and the
   diagrams (as below). These will be re-generated with a new build,
   and deleting the old content now gets rid of all the stubs for objects
   which have since been removed and ensures all diagrams contained in the
   directory will be up-to-date. Specifically, remove as follows:

   ```console
   $ rm -rf source/_autosummary/
   $ rm -rf source/uml_images/
   ```

   See
   [this commit](https://github.com/IDAS-Durham/JUNE/pull/401/commits/64f6bce1eb9fa4a2900647984a45c8250f2c52de)
   for an example.

6. Now try a rebuild:

   ```console
   $ cd <path to JUNE>/JUNE/docs
   $ make clean
   $ make html
   ```

   If all objects no longer in the codebase API have been detected and
   removed properly, as per steps (1), (2) and (4), the
   build should now pass (i.e. with no errors, but lots of warnings are
   likely for formatting of docstrings). Otherwise, something may need
   amending, so check through the steps again and heed any errors the
   build outputs to STDERR.

7. When the build passes, view the generated HTML documentation in the
   browser, as per the [section above](viewing-the-built-html), to check
   that they look as they should generally, and eyeball the diagrams pages,
   to see that they are.
