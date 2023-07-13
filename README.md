fladrif
=======

Quick and dirty library to generate a ["patch"] transforming one tree into
another. Heavily based on [`rstdiff`] by Stefan Merten.

## Usage

Subclass `fladrif.treediff.Adapter` to connect your tree objects to the
algorithm in this package.

Then, use `fladrif.treediff.TreeMatcher` to compute the set of operations in the
patch.

Finally, you can subclass `fladrif.apply.Apply` to walk the operations to build
a new tree.


["patch"]: https://en.wikipedia.org/wiki/Patch_(computing)
[`rstdiff`]: https://docutils.sourceforge.io/sandbox/rstdiff/
