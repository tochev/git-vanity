# git-vanity #

**git-vanity** is a tool for generating git commit hashes with a pre-specified prefix (*vanity commits*).

This is done either by adding a string to the committer's name (note that the visualization utilities usually show the author's name) or by adding custom data to the commit's header.

*Homepage:* https://github.com/tochev/git-vanity

Demo: https://github.com/tochev/git_vanity_demo


## Install ##

Install `python3`, `pyopencl`, `numpy`, and `opencl`:

    # substitute amd for nvidia if you have nvidia gpu
    apt-get install amd-libopencl1 amd-opencl-icd
    apt-get install python3 python3-numpy python3-pyopencl

Get the project:

    git clone https://github.com/tochev/git-vanity

In order to use the GPU you will need drivers that support OpenCL, which at the moment means that for Radeon you will need the proprietary ones (fglrx).

Optional: create `git-vanity` symlink to `git_vanity.py` in order to be able to call `git vanity`:

    sudo ln -s GIT_VANITY_DIR/git_vanity.py /usr/bin/git-vanity

Optional: export `PYOPENCL_CTX` to avoid being prompted for the OpenCL device to be used (`git-vanity` will prompt you on the first run and display the appropriate information).


## Example Usage ##

### Usage ###

    $ git-vanity --help
    usage: git-vanity [-h] [-s START] [-g GS] [-w WS] [-W] [-q] [-r] [--version]
                      hex_prefix

    Create vanity commits by extending the committer's name or the commit object.

    positional arguments:
      hex_prefix            the desired hex prefix

    optional arguments:
      -h, --help            show this help message and exit
      -s START, --start START
                            start the search from number (hex)
      -g GS, --global-size GS
                            OpenCL global size (use carefully)
      -w WS, --work-size WS
                            OpenCL work size (64,128,256,...)
      -W, --write           write to the repo
      -q, --quiet           quiet mode, disables progress
      -r, --raw             change the raw commit instead of the committer
      --version             show program's version number and exit


    $ git deadbeef -W # change HEAD to commit having id starting with deadbeef
    ...

    $ git log | head -n 1
    commit deadbeefe959dfe56e86a483a344ca582e0b74c

### Example ###

    $ git log
    commit 557d8de0090428e170e548131c80fcb0d822545b
    Author: John Doe <john.doe@example.com>
    Date:   Sun Apr 13 17:02:19 2014 +0300

        00000000

    commit ffffffff1eee2fa663259abd075621d32d46a16d
    Author: John Doe <john.doe@example.com>
    Date:   Sun Apr 13 16:47:57 2014 +0300

        Add file b.txt

        Very interesting commit by John Doe.

    commit ffffffff204994fae3843df6c5be753e88ced44b
    Author: John Doe <john.doe@example.com>
    Date:   Sun Apr 13 16:43:56 2014 +0300

        initial commit

    $ git vanity 00000000 -q -W
    Attempting to find sha1 prefix `00000000'
    for commit `557d8de0090428e170e548131c80fcb0d822545b'
    ================
    tree d11b5fac254c4b7a5a8e078cbad43ba15d6494ff
    parent ffffffff1eee2fa663259abd075621d32d46a16d
    author John Doe <john.doe@example.com> 1397397739 +0300
    committer John Doe <john.doe@example.com> 1397397739 +0300

    00000000
    ================
    ...

    Found sha1 prefix `00000000'
    with sha1 `00000000b2c4731e107f28abfff83f53816b305a'
    Using 00000000007716D6
    ================
    tree d11b5fac254c4b7a5a8e078cbad43ba15d6494ff
    parent ffffffff1eee2fa663259abd075621d32d46a16d
    author John Doe <john.doe@example.com> 1397397739 +0300
    committer John Doe 00000000007716D6 <john.doe@example.com> 1397397739 +0300

    00000000
    ================


    Writing changes to the repository...

    John Doe 00000000007716D6
    [master 0000000] 00000000
     Author: John Doe <john.doe@example.com>
     1 file changed, 1 insertion(+)
     create mode 100644 c.txt
    Current HEAD:
    00000000b2c4731e107f28abfff83f53816b305a
    All done.

    $ git log
    commit 00000000b2c4731e107f28abfff83f53816b305a
    Author: John Doe <john.doe@example.com>
    Date:   Sun Apr 13 17:02:19 2014 +0300

        00000000

    commit ffffffff1eee2fa663259abd075621d32d46a16d
    ...


## How does it work? ##

**git-vanity** amends the last commit to have a hash that matches a particular prefix.

This is achieved by appending a 64bit number in hexadecimal notation to the committer's name, which is not normally shown. Alternatively, another option offered by git-vanity is to add a vanity field containing a 64bit number to the commit header, which, though unlikely, might interfere with low-level git software or future git versions.

Example: the repository before the change looks like:

    $ git cat-file -p HEAD
    tree 468948f9e6b55bd3514f554c1c34cbca70a0821f
    parent 00000000b2c4731e107f28abfff83f53816b305a
    author John Doe <john.doe@example.com> 1397400447 +0300
    committer John Doe <john.doe@example.com> 1397400447 +0300

    add random file

After `git vanity deadbeef -W` we get:

    $ git show-ref -s HEAD --head
    deadbeef0c84b5c33941939582d574c7ddcde9e4

    $ git cat-file -p HEAD
    tree 468948f9e6b55bd3514f554c1c34cbca70a0821f
    parent 00000000b2c4731e107f28abfff83f53816b305a
    author John Doe <john.doe@example.com> 1397400447 +0300
    committer John Doe 0000000000A92AB3 <john.doe@example.com> 1397400447 +0300

    add random file


## Related Work ##

 - bitcoin and litecoin vanity address generators
 - [vanitygen](https://github.com/samr7/vanitygen) bitcoin address generator
 - [gitbrute](https://github.com/bradfitz/gitbrute/) CPU vanity git commit generator using committer and author timestamps

## License ##

Distributed under GPL3.

Need another license - I'm flexible - send me an email.


## Authors ##

Developed by Tocho Tochev [tocho AT tochev DOT net].


## FAQ ##

#### Why OpenCL and not pure CPU? ####

For these types of computations OpenCL is much faster.
Besides I needed a toy project for playing around with OpenCL.

#### Why the change to the commit is done in this way? ####

If one is to adhere to the human git interface one can change the author's/committer's names and emails and the two timestamps.

There are several reasons to append a fixed-width number to the committer name:

 - the timestamps are preserved
 - the emails are preserved
 - no information is lost
 - it is easy to automatically process it (auto-striping, extracting the original committer, etc.)
 - it is revertible
 - successive `git-vanity` applications need not further mangle the commit, they can just use the already allocated space for the number
 - 64 bits should be sufficient for the computationally feasible search space at the moment, and besides one can always tweak the committer name further
 - the length of the data during the search does not change, resulting in faster computation

#### What are the consequences of changing the raw commit? ####

At the moment all of the software I'm aware of has not problems dealing with the changes introduced by git vanity. However, one should be aware of the remote possibility of problems with future git versions or low-level git tools.

Use raw commit changes at your own risk.

#### Which commits can be changed? ####

Currently only the HEAD is changed but by manually switching the HEAD one can change all revisions.

#### How fast is it? ####

It depends on your hardware and of course on the length of the commit message, but on a Radeon HD 7750 with a short commit message it does about 70MHash/s, dropping to about 40MHash/s for the long commit messages.

There is a lot of luck involved with finding a matching hash. Therefore, making estimations about the remaining time is prone to error.

When searching prefix of length `X` bits there `2^140 - 2^(140 - X)` hashes that do not match it.
At each step the chance of finding a matching prefix is assumed to be around `2^X`.

Under the *wrong* assumption that each successive change to the number added to the committer's name gives unique prefix we should find a hash within `2^X` tries (displayed as "tries remaining").

If one assumes that the hash values are uniformly distributed, the probability of `Y` consecutive prefix failures and then success is `1 - (1 - 1/2^X)^Y` (displayed as "Chance (CDF)". This statistic has proven itself valid by the bitcoin community for the sha256 hash.

Generally finding a 32-bit (8-symbol) prefix on Radeon HD 7750 takes a minute-two, while a 40-bit one (10-symbol, as displayed by github) should reach `2^40` hashes tried (`CDF=0.63`) in about 4-8 hours.

#### Why isn't there an estimated time and why does the progress show strange numbers? ####

See the previous question.

#### Does it work with GPG singed commits? ####

Yes, but only in raw commit mode, otherwise the program will not work correctly on a signed commit.

If you apply committer name vanity search on a signed commit you must first remove the signature (you can use `git vanity 0 -W`) and then run it for the desired prefix.

#### Will it always find a hash? ####

The short answer is that if the prefix is short - yes, if it is not - it is up to your luck.

The more elaborate answer is that it tries up to `2^64` changes to the message (which is infeasible on the current home hardware). The chances are that for short prefixes (32 bits) a solution will be found quickly, but for longer ones (48 bits) it might just take too long. Also if you give it insufficient search space by setting start too close to `MAX_UINT64` it will most likely fail to find a solution.

#### Any risks involved? ####

The source code is safe in that it will not damage any data.

Since the program forces the hardware to work hard it needs sufficient cooling. This should not be a problem for cards running with stock settings in well ventilated environment. The rule of the thumb is that if your hardware can do bitcoin/litecoin mining it can handle this vanity search.

That being said, due to potential bugs in the GPU drivers it is possible, although highly unlikely, for the X to crash, for the computer to freeze, etc. A restart will fix the problem and then you can try to tweak down the global and work sizes.

#### It is causing CPU load and seems slow. ####

Sometimes the OpenCL support for the GPU might not be installed or configured correctly. Make sure that the GPU is listed by `clinfo` and that `git-vanity PREFIX` states that it is using the GPU (`Using device: '...' (device type: GPU)`).

#### It did not work correctly. ####

As with any software bugs happen.

If it seems that the bug is related to code running on the GPU please restart the PC (to rule out any temporally problems in the drivers) and try without any overclocking.

If the problem persists please send me the output of `git cat-file -p HEAD`, your command line, information about your setup (hardware, X, drivers, the output of `clinfo`), and any errors.
I will try to replicate the problem but finding similar setup might be hard.

#### Can I use the CPU? ####

If you have a modern CPU most likely the answer is yes, but it will be very slow compared to the GPU and probably less efficient than a CPU-targeted option.

#### I have a comment. ####

Drop me a mail.

#### Ok, I want to help. What can I do? ####

You can:

 - spread the word
 - tip me in bitcoin: 1BrWMW6s6Z6EoJobrGZELvnjj8pjS1o5BH or litecoin: LUHDByhZzjaAhnfgnziUpgwuncymRq9qVM
 - take a look at the list of TODOs and help with something, I accept patches
 - suggest an improvement


## TODOs ##

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
 - rudimentary regex support for the target and optimization
 - manpage, package, etc
 - rewrite in C :)
