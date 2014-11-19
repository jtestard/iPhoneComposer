## Preview of next generation iPhoneComposer

### Naming conventions

Some naming conventions used throughout this presentation to identify components of the application are described here. This is a first attempt to "formalize" the design of the application (Note to self: in the future, the notation should be aligned as much as possible with AthenaCL).

- *Note generation* : in iPhoneComposer, the musical composition is created through live MIDI note generation.
- *Musical Features* : in iPhoneComposer, the note generation originates from musical feature configurations. Each musical feature can then be configured independently. There are currenlty 6 controllable musical features used for the note generation:
    - *Path* : describes the notes used, expressed in musical format (i.e. 'C3', 'D#4'...).
    - *Rhythm* : describes the rhythmic patterns used.
    - *Pitch* : describes the pitch modulation patterns used.
    - *Amplitude* : describes the amplitude patterns used.
    - *Instrument* : describes the MIDI instrument used.
    - *BPM* : describes the bpm used.
- *Atom* : smallest element of a musical feature which can be configured. What an atom corresponds to may be different for each musical feature (e.g. a pitch such as 'C3' is an atom for a path, an float such as 0.51 for an amplitude).
- *Pattern* : the set of atoms for a given feature.
- *Pattern Board* : the component of the device user interface with which the user configures the pattern of a given musical feature. Pattern boards are typically made of a rectangle of cells which can be selected by tapping them.
- *Selection Mode* : the selection mode describes the way the next element will be chosen from a pattern for the note generation.
- *Selector* : the component of the device user interface which represents the current selection mode.
- *Tab* : a tab exists on the device user interface for each musical feature and describes the configuration for that feature. Some features, such as BPM and Instrument, are on the same tab (called Basic).

### Part 1 : Algorithm generation

Up to now, the only to provide non-determinism in the iPhoneComposer application was by using choosing a non-cyclic selection mode (such as uniform random). In particular, the pattern configuration happens entirely manually and this reduces greatly the "compositional" aspect of the application. As such we add a new component to the device user interface, the *Algorithm Board*.

The *Algorithm Board* describes algorithms which alter musical feature patterns. Selecting and applying an algorithm can be done simply by tapping on the desired algorithm cell within the board. The algorithm will take the existing pattern and change it according to its internal logic. 

An example of python source code for the left phase shift algorithm :

```python
def algorithm(pattern):
  # pattern = ['C3', 'S', 'C4', 'C3', 'S', 'C4', 'C3', 'S']
  shift(pattern,1)
  # pattern = ['S', 'C3', 'S', 'C4', 'C3', 'S', 'C4', 'C3']
  return pattern
```

A new tap on the algorithm board would apply the algorithm on the new pattern. The algorithmic pattern follows a feedback loop :

![Algorithm feedback loop](./images/algorithm_feedback_loop.png)

Currenlty, only two algorithms will be implemented : left and right phase shifting.

### Part 2 : Interface changes

In this section, we describe the changes made to the device user interface. Each subsection is accompanied with a screenshot of what the new interface will look like on an iPad.

#### Instruments and Presets

The instrument selection has be changed from an analog dial to a 2 dimensional board. The dial selection made it easy to miss the instrument selection by one, which would lead to unfortunate consequences during a performance :). The BPM analog dial has been kept. A few button to play, pause, mute or unmute the application have been added.

A major addition is the presence of presets. Only preset *loading* is currently planned. Presets can be written in YAML files and will be loaded according to their filename. The preset file must reside in the preset folder. A `-preset-folder` option has been added to the program arguments.

The contents of a preset file will look as follows :

```yaml
instrument: 45
bpm : 110
rhythm :
  dividor : 4
  list : [
  	[1,0,0,0,1,0,0,0],
  	[1,0,0,1,0,1,0,1],
  	[1,0,0,0,1,0,0,0],
  	[1,0,0,1,0,1,0,1]
  ]
  order : 
    type : cyclic
path: 
  list: ['C3', 'S', 'C4', 'C3', 'S', 'C4', 'C3', 'S']
  order : 
    type : cyclic 
pitch:
  list: [0,0,0,2,3,-2,0] 
  order: 
    type: random
amplitude:
  list : [0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5]
  order:
    type: cyclic
```

![The Basic Tab](./images/basic.png)


#### Path

The path pattern board remains mostly unchanged. The support for the markov selector has been removed (for all patterns, not just path). The "other" selector currenlty only replicates the cyclic selector behavior. A novelty is the *Position Indicator*.

The position indicator can be seen just under the current path in the screenshot. When the application is running, the currently played atom in the pattern is highlighted. This will help the performer to follow what the application is doing visually.

Finally, the algorithm board for the path pattern can be seen on the bottom of the application. Tapping on an "undefined" algorithm will do nothing.


![The Path Tab](./images/path.png)


#### Rhythm

The rhythm pattern now uses an 8x4 2D grid instead of 16 sliders. The semantics of the grid are as follows :

 - Each row in the grid correspond to a rhythmic pattern. This pattern is always played in its entirety, it does not depend on the current selection mode. For example, the first row in the rhythm figure (before the phase shift) corresponds to two quarter notes (assuming dividor is 4).
 - The order in which rows are played is determined by the selection mode. The currenlty played pattern is displayed by the position indicator on the top left of the figure.
 
An important note is that empty cells on the grid do not correspond to a silence (as is usual in these kind of interfaces). Rather, it should be understood as an "absence of new onset". In order to specify a silence, the user should include the 'S' note in his path. The two following figures show what the rhythm tab would look like before and after tapping on the shift right algorithm.

![Rhythm Phased before phase shift](./images/rhythm_phase_shifted.png)

![Rhythm Tab after phase shift](./images/rhythm.png)

The new rhythmic pattern display has been prefered over the previous for the following reasons :

 - The previous pattern had no guarantee that the sum of all the generated durations would correspond to a bar, and made such an operation difficult.
 - Dragging a slider too much or too little would result in an immediate and most likely unwanted loss of rhythmic cohesion.
 - The new interface makes it easy to avoid such cohesion loss and guarantees that the sum of generated durations will always correspond to a bar.
 - This new interface is also easier to manipulate in the context of cellular automata.

#### Pitch

The pitch patterns now uses a 8x7 grid instead of 16 sliders. The semantics of the grid are as follows :

 - Each column in the grid corresponds to a pitch modulation. The amount of pitch modulation is indicated on the right side of the tab. If multiple cells are selected for a given column, then *ALL* pitch modulations indicated by the selected cells are played at the same time. This essentially enables polyphony.


![The Pitch Tab](./images/pitch.png)


#### Amplitude

The amplitude tab hasn't been changed, besides the addition of the position indicator.


![The Amplitude Tab](./images/amplitude.png)







