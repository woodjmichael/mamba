# Quickstart

mamba.py v7.x | Michael Wood | 2021.5.x




## Overview
The 'mamba dispatch' software uses simplified dispatch strategies for very fast simulation of utility connected or islanded microgrids. Peak shaving and arbitrage are the two main strategies. Mamba is written for and tested using Python 3.8.

1. **Single Simulation, or 'run'.**
  - For utility connected simulation we simply calculate the residual load (actual load less PV production) and make a decision to dispatch the battery based on the selected strategy - any available generator is probably not used. This simulation can be anywhere from a few timesteps to a year long.
  - For resilience simulations we initiate a grid outage at time t, and then simulate the PV-battery-generator microgrid for a reasonable time period, say two weeks. At the end we are given basic information about how long until the microgrid failed to serve the load (Time to First Failure) and of the whole time period how much time the load was served.
2. **Year of Resilience Simulations.** A single outage is interesting, but we really want to know how our microgrid will perform at any time of the year. So we simulate one outage at Jan 1 0:00, then another at  Jan 1 3:00, then Jan 1 6:00, all the way to Dec 31 23:00. And by default we jump in 3 hr increments. A year takes about one minute to simulate. This does not apply to utility connected cases.
3. **Matrix of Simulated Years, or 'superloop'.** The year of outages was only for a single given battery size, PV size, and generator size (could be 0). If you want to know the results for an NxM matrix of battery and PV sizes, run a superloop. In this version a generator axis is not implemented.



## Setup

### Installing Python

The internet is not-literally full of great ways to get Python 3 on your machine, but Visual Studio Code (editor) and Anaconda/Conda (environment manager, helps install difficult packages) are fantastic.

### Dependencies

The only non-standard package should be numpy, which Anaconda can help install. But on a clean Python 3 install pip (or the windows equivalent) could be quicker:

`pip install numpy`

All the commands in this doc are from the normal macOS terminal.

### Input Data

Input load and solar data should be a single year of 15-minute interval and in units of kW. Solar can also be in capacity factor (normalized to the physical plant capacity "kWp") if used with the PV scaling factor (see Program Arguments). The site name ("[client]_[building]" identifier) is used by mamba to find the solar and load files. See `Profiles VC` directory for templates.

Mamba creates datetime stamps for output data where the time instant is the **beginning** of the 15-minute interval for which the data is valid.

#### *Example:*

```
  Datetime,load kW
  2019/1/1 00:00, 21.6
  2019/1/1 00:15, 18.9
```

*The above 21.6 kW of load is valid from 2019/1/1 0:00:00 to 2019/1/1 00:14:59.999... and then at exactly 2019/1/1 00:15:00 the load changes to 18.9.*

#### Two Conventions

- We sometimes call this the above example "Beginning of Period (BOP)" convention. Mamba uses this.
- Redcloud and the associated LINKED RESULTS files use "End of Period (EOP)" convention.

This shouldn't matter, if both programs make their calculations knowing their own convention, and the user knows the convention of the outputs.

But for the **input data** it's important to use **consistent** convention data. So find either **all BOP** or **all EOP** data. One way to do this is pull all your input data from a LINKED RESULTS file.


## Running

### Inputs

Besides input data, the most important considerations are choosing the simulation type and defining the simulation parameters. You could always edit these in the script directly. But giving command line arguments should be faster, clearer, and avoid mistakes.

* Program Arguments are used to tell mamba what to simulate and how, see below for more.

* Basic example argument list. In order: simulation type, site, battery power, battery energy, generator power, generator tank size, generator fuel is propane.

  `python mamba.py -s badriver_clinic r -b 200 580 -gp 200 400`

* For sites without a generator, the generator power **is set by default** to 0.

* To run a superloop you can provide the vectors of generator, battery, solar, and load sizes as program arguments. Or you may need to edit the code directly. Search on 'if superloop enabled' and remember to include the superloop flag for a successful execution:

  `python mamba.py -s fish r -sl`

  * When running a superloop, consider first testing your matrix of pv-battery sizes with a single run per Simulated 'Year'. If you messed up, you'll know a lot sooner. Example:

    `python mamba.py -s fish r -sl -r 1`

### Errors

In general _do_ pay attention to errors output at the end of your simulation. We can mute errors that are repeated and annoying to avoid the Chernobyl problem (habitually ignoring error lights as false positives).



## Analysis


### Outputs
Harkening back to the three nested loops, we have:

1. **Single Simulation, or 'run.'** The file vectors.csv (off by default) gives you all the dispatch info for a single two-week outage. Warning: only turn this on for a single simulation, or the code will run a lot slower. This is because normally we simulate 2920 (a whole year, in 3 hr increments) at a time, so we throw out the dispatch data for speed. Try:

	`	python mamba.py -s badriver_clinic r -b 200 580 -r 1 -v`

With the above arguments you'll get only the 14-day dispatch starting at 12am Jan. To skip ahead 24 hours and get the 3 day dispatch do:

	python mamba.py -s badriver_clinic r -b 200 580 -r 1 -sk 24 --days 3

2. **Year of Resilience Simulations (default).** Always produced by default, output.csv contains a year of time to first failure and cumulative operating time data for your chosen pv-battery-generator size. Each row of data is for one Single Outage.

3. **Matrix of Simulated Years, or 'superloop.'** Each superloop.csv row represents a Simulated Year of outages, summarized with confidence and TTFF statistics. Clearly this file is only output with the -sl flag.

## Program Arguments   
Program arguments are best issued in this order, with the values following directly after keys
`python mamba.py -s mugrid_test r -b 1.5 -be 3 .. (etc)`

### Typical

| Description         | Structure                  | Example          |
| ------------------- | -------------------------- | ---------------- |
| Site and simulation | -s  [sitename] [sim]       | -s mugrid_test r |
| Battery             | -b [power kW] [energy kwh] | -b 60 120        |
| Generator           | -g [power kW] [tank gal]   | -g 50 200        |

### Alternative

| Description | Structure         | Example        |
| ----------- | ----------------- | -------------- |
| Site        | -s  [sitename]    | -s mugrid_test |
| Simulation  | -sim [simulation] | -sim r         |



### Optional (must come after -s or -sim)

```
Simulation resilience multiple generators
                          -sim rmg [gen1 power, gen1 tank, gen1 fuel type, gen2 power, gen2 tank, gen2 fuel type]
                                                      e.g. -sim rmg 20 100 d 50 200 p
Run "n" simulations:    -r [n]                      e.g. -r 1           default=2920
Dispatch vectors ON:    -v                          e.g. -v             default=OFF
Battery vector ON:      -vb                         e.g. -vb            default=OFF
Load stats ON:          --loadstats                 e.g. --loadstats    default=OFF
Skip ahead "h" hours:   -sk [h]                     e.g. -sk 24         default=OFF
Superloop enable:       -sl                         e.g. -sl            default=OFF
Enable battery daytime generator charging:
                        -bdg                        e.g. -bdg           default=OFF
Gen fuel is propane:    -gfp                        e.g. -gfp           default=OFF
Days to simulate:       --days [days]               e.g. --days 3       default=365
Battery depth of dischg:-bd [dod]                   e.g. -bd 0.95       default=1.0
      -bd must come after -be because it modifies battery energy
      NB: -bd just changes the battery energy, so soc will still be 0-100%
Plots ON (option to plot normal or utility first):
                          --plots [ | u]              e.g. --plots        default=OFF
Debug (see code):        --debug [ | type]           e.g. --debug res    default=OFF

  
```

