# Changelog

Important changes from the changelog are summarized here. See GitHub repository for [detailed changelog](https://github.com/geddy11/sysloss/blob/main/CHANGELOG.md).

## Version 1.9
New features:
  * `utils` package. Function for calculating PCB trace resistance
  * Heat diagram function, `make_hdiag()`

## Version 1.8
New features:
  * Component PMux (Power Multiplexer)
  * Component Rectifier - diode and MOSFET modes
  * Source component can now have load phases defined

## Version 1.7
New features:
  * Add "loss" parameter to all loads, optionally configuring power as a loss
  * Add `.rail_rep()` method to `System` (voltage rail report)
  * Add group parameter to `make_diag()` function
  * Add the option to add voltage rail names in `System`
  * Allow power rail name as parent parameter in `add_comp()`, `change_comp()`

## Version 1.6
New features:
  * Add graphical power tree diagrams module
  * Add group parameter in `System`, allowing grouping of components

## Version 1.5
New features:
  * Add method `.limits()` to system, which returns all user defined component limits
  * Component PSwitch (Power Switch)
  * New limit added: `vd` (voltage difference)

## Version 1.4
New features:
  * Add ambient temperature (ta) as new parameter to `.solve()` and peak temperature (tp) as a new limit

## Version 1.3
New features:
  * Add tags argument to `.batt_life()`
  * Add thermal resistance parameter and temperature rise calculation

## Version 1.2
New features:
  * Add power limits to all components (pi, po, pl)
  * Add interpolation option to `LinReg` ground current parameter

## Version 1.1
New features:
  * New method `.batt_life()` to estimate battery lifetime 
