git-vanity
==========

*git-vanity* is a tool for generating git commits with a pre-specified prefix
by adding a string to the committer's name.
We will call these commit hashes *vanity commits*.


Installing
----------

TODO: OpenCL requirements, git-vanity symlink


Example Usage
-------------

TODO: raw code, before, during, after,


How does it work?
-----------------


Related Work
------------
 - bitcoin and litecoin vanity address generators
 - [vanitygen](https://github.com/samr7/vanitygen) bitcoin address generator
 - [gitbrute](https://github.com/bradfitz/gitbrute/) CPU vanity git commit generator using committer and author timestamps


FAQ
----

#### Why OpenCL and not pure CPU?

#### Why the change to the commit is done in this way?

#### How fast is it?

#### Any risks involved?

#### It did not work correctly.

#### I have comment.


TODOs
-----
 - better probability-based counter
 - better precision in the counters
 - add quiet mode
 - use logging
 - write tests
 - add more error handling
 - auto-optimization of GS and WS
 - add for support other revisions than the HEAD
 - add more documentation (as usual)
 - add option for length of the name addition
 - cl kernel: export the sha1 compute cycle to function, fill W boxes better
 - !!! rewrite in C :)
