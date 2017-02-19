Qommitter
=========

Qommitter is a simple commit editor for GNU/Linux. I decided to write it
because I can't decide what to choose between a ncurses editor or a GUI
based one. None of them was satisfying me enough.

Features
--------

-  Syntax highlighting for:

   -  comments
   -  "standard" git summary recognition and length (50 characters)
   -  "standard" extended length (72)
   -  tabs and trailing spaces

-  Undo/Redo support
-  Size/line/line length count

Requirements
------------

-  Python 2.7
-  PyQt4 >= 4.11.1

Usage
-----

``git clone`` the repository and create an alias for it. For example, if
you cloned it on ``~/local/Qommitter/``, add this line to your
``~/.bashrc`` file

::

    alias qommitter='GIT_EDITOR='~/local/Qommitter/__init__.py' git commit'

then logout and login again, or run this in the current console:

::

    $ . ~/.bashrc

after that, you only need to run ``qommitter`` from a (sub)directory of
a git repo. Use ctrl+s to save the commit message. Of course, you can
choose any name you want instead of ``qommitter``.

Qommitter might be used as a default editor for git, but I've not tested
it yet, so do it at your own risk.

(Almost) known issues
---------------------

Text encoding is still experimental, my system uses utf-8 by default,
and errors might occurs if you use other character encodings. Feel free
to submit any issue.
