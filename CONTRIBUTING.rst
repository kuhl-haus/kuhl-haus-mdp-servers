============
Contributing
============

Welcome to ``kuhl-haus-mdp-servers`` contributor's guide.

Please notice, all users and contributors are expected to be **open,
considerate, reasonable, and respectful**. When in doubt, `Python Software
Foundation's Code of Conduct`_ is a good reference in terms of behavior
guidelines.


Issue Reports
=============

If you experience bugs or general issues with ``kuhl-haus-mdp-servers``, please have a look
on the `issue tracker`_. If you don't see anything useful there, please feel
free to fire an issue report.


Code Contributions
==================

Before diving in, please review the README_ for an overview of the system
architecture, component descriptions, and data flow. Full documentation lives
in `kuhl-haus-mdp`_.

#. Create a branch to hold your changes::

    git checkout -b my-feature

   Never work on the main branch!

#. When you're done editing::

    git add <MODIFIED FILES>
    git commit

#. Run the unit tests::

    pdm run pytest tests -v

#. Push your branch and open a pull request targeting ``mainline``.


Maintainer tasks
================

Releases
--------

If you are part of the group of maintainers and have correct user permissions
on PyPI_, the following steps can be used to release a new version for
``kuhl-haus-mdp-servers``:

#. Make sure all workflows for the latest commit are successful.

#. Generate release notes by running the changelog script with the appropriate version bump:

   **Linux / macOS / Windows with WSLv2:**

   .. code-block:: bash

      # For a patch release (e.g., 0.2.28 → 0.2.29)
      ./update-changelog.sh --bump patch

      # For a minor release (e.g., 0.2.28 → 0.3.0)
      ./update-changelog.sh --bump minor

      # For a major release (e.g., 0.2.28 → 1.0.0)
      ./update-changelog.sh --bump major

   The script will generate a new version section in ``CHANGELOG.rst`` with all
   commits since the last tagged release.

#. Review the generated ``CHANGELOG.rst``, commit it, and create a pull request
   targeting the mainline branch.

#. After the PR is merged, tag the merge commit on the mainline branch with the
   corresponding release tag, e.g., ``v1.2.3``.

#. Push the new tag to the upstream repository_, e.g., ``git push upstream v1.2.3``

#. The `publish-to-pypi`_ GitHub Actions workflow will build and upload the
   package automatically.


.. _repository: https://github.com/kuhl-haus/kuhl-haus-mdp-servers
.. _issue tracker: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/issues
.. _publish-to-pypi: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/actions/workflows/publish-to-pypi.yml
.. _README: https://github.com/kuhl-haus/kuhl-haus-mdp-servers/blob/mainline/README.rst
.. _kuhl-haus-mdp: https://github.com/kuhl-haus/kuhl-haus-mdp
.. _Python Software Foundation's Code of Conduct: https://www.python.org/psf/conduct/
.. _PyPI: https://pypi.org/
