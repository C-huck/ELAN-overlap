# ELAN-overlap
Allows users to extract temporal information between annotations on different tiers in ELAN. Useful for quickly quantifying simultaneous actions (e.g., speech + gesture, joint attention + touching, facial expressions + speech).

An example is given in the following images: (left/above) Screenshot of part of the ELAN interface, showing complicated temporal overlaps between annotations on different tiers. (right/below) One possible output of ELAN-overlap: listing pairwise overlaps of annotations on the 2nd and 3rd tiers, the type of overlap, and the duration of the overlap. 

![Screenshot of ELAN](https://github.com/C-huck/C-huck.github.io/raw/master/images/elan.PNG) ![Screenshot of ELAN-overlap output](https://github.com/C-huck/C-huck.github.io/raw/master/images/elan2.PNG)


  
## Version 2 (ELAN_overlap.py)
So far:
  - [x] reports annotations of a single tier and their frequencies
  - [x] reports number of overlaps between user-specified number of tiers; prints all overlapping annotations
  - [x] reports annotations overlapping a user-specified annotation
  
 New (09/14/20):
  - [x] incorporated Version 1 (overlap.py) functionality into `ELAN_overlap.py`
  - [x] bug fix: Child and grandchild tiers now supported
  - [x] bug fix: Empty tiers (i.e., have no annotations) are now dropped
  - [x] removed semi-functional `reset` function
  
 New (09/19/20):
   - [x] added overlap duration information to `get_overlaps()` and `word_search()`
   - [x] tier names now clipped in console display if over 20 characters

To do:
  - [ ] overhaul results display and saving functions (too many exported .csv files, etc.)
  - [ ] graphical output


# Instructions for use (v2):
`overlap_v2.py` is written in Python 3 (3.7.3), and uses `bs4` (BeautifulSoup) with the `lxml` parser, `numpy`, `pandas`, `glob`, `collections`, and `itertools`. Read/ write access to the working directory is required. 

Download `ELAN_overlap.py` to a folder containing the .eaf files you want to analyze. Run the file using a command window and follow the prompts on the console. 

1. Choose file (must be an .eaf file).
2. Choose temporal resolution, in msec. The algorithm reconstructs the eaf file as a matrix at the given resolution. If your annotations are fine-grained, use 1. Note that building the matrix will take longer at shorter temporal resolutions, but accuracy is much higher. 
3. Choose tiers to include. You may choose an arbitrary number of tiers to include. Include all by typing 'all' (without quotes). Note that the matrix is built only once. If you choose 'all', you can later search any subset of tiers. If you choose some subset at the start, only those tiers are available to search later. **Support for up to 13 tiers only.**
4. Main functions:
   - `get_annotations()`: Returns the frequency of each annotation on a user-specified tier
   - `get_overlaps()`: Returns the number of overlaps (and overlapping annotations) between a user-specified set of tiers
   - `word_search()`: Returns the annotations that overlap a user-specified word and the frequency of overlap
   - `get_overlap_relations()`: Returns overlaps between exactly two tiers, the type of overlap (right edge, left edge, contains, is-contained, and is-isometric-with), and duration of overlaps
   - `quit()`: Destroys matrices and exists
5. Sub function:
   - `prune_short_annotations()`: Calculates the duration of each overlap and excludes those shorter than a set threshold. The user may choose a threshold (in whatever temporal resolution the matrix was constructed in) or choose 'auto.' 'Auto' excludes overlaps that are one standard deviation shorter than the mean overlap duration. Called when executing the `overlaps()` function (the basis of `get_overlaps()` and `word_search()`)
6. Available options:
   - `iterate`: The `get_overlaps()` function allows you to return overlap data for every combination of user-selected tiers. E.g., if `Tier0`, `Tier1`, and `Tier2` are selected, the function returns annotation frequencies for each and overlap frequencies for `Tier0`-`Tier1`, `Tier1`-`Tier2`, and `Tier0`-`Tier1`-`Tier2`.
   
Results are saved as `.csv` files according to the following scheme: input filename + analysis + selected tiers .csv. For the iteration option, the output scheme is: input filename + iteration number . csv. 

### Tips:

1. The inclusion of >13 tiers is unsupported.
2. `get_overlaps()` returns a 'hit' iff there is an overlap between each selected tier at a given time. Annotations that transitively overlap (e.g., Annot A overlaps Annot B, Annot B overlaps Annot C, but Annot C does not overlap Annot A) are not counted. 

## ~~Version 1 (overlap.py)~~ incorporated into `ELAN_overlap.py`
So far:
  - [x] reports overlaps between two tiers
  - [x] reports type of overlap (right edge, left edge, contains and is-contained
  - [x] reports duration of overlaps
  
To do:
  - [ ] flexibly apply algorithm to user-specified number of tiers
  - [ ] add keyword search
