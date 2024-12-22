# Changelog


## v1.8.0 (2024-12-21)

### Documentation

- Add Rectifier to component parameter files tutorial
  ([`73f2be9`](https://github.com/geddy11/sysloss/commit/73f2be947699ccb324ec337a6a35e470b67cf284))

- New tutorial: power over ethernet analysis
  ([`cce4a1f`](https://github.com/geddy11/sysloss/commit/cce4a1fca20139c9a79bbac2b15a0fc86f0723c7))

### Features

- New component PMux (Power Multiplexer)
  ([`ad3079f`](https://github.com/geddy11/sysloss/commit/ad3079f7a84d7a7bbbd482b0ffe2f42d0dcd1956))

- New component Rectifier - diode and MOSFET modes
  ([`2e4ea83`](https://github.com/geddy11/sysloss/commit/2e4ea834e0a3acd225e61bd348058651cef68076))

- Source component can now have load phases defined
  ([`653321d`](https://github.com/geddy11/sysloss/commit/653321df33ada9688e3ccd446bce5e5d629ed161))

### Refactoring

- Add check for component interpolation data format
  ([`b5575f7`](https://github.com/geddy11/sysloss/commit/b5575f7f1aa41b9da3f53ec7b8db2cd113f7f3af))

- Change to generic .from_file() method in Component class
  ([`ad4b91d`](https://github.com/geddy11/sysloss/commit/ad4b91d2f0b0f1912016ec7a541931c34baff935))


## v1.7.0 (2024-11-10)

### Bug Fixes

- Add loss parameter reading to System.from_file()
  ([`94b419a`](https://github.com/geddy11/sysloss/commit/94b419a3cddeaae62d509d32616f4a99cf8f5aa4))

### Continuous Integration

- Remove sudo from readthedocs .yml
  ([`2e17b54`](https://github.com/geddy11/sysloss/commit/2e17b543524a8ab2102cf743cf33934abb7db0fe))

- Use "apt_packages" to install graphviz for rtd
  ([`41168e0`](https://github.com/geddy11/sysloss/commit/41168e0e559be9c5e52e707bcebb5e21df1d75d5))

### Documentation

- Update readme.md with make_diag()
  ([`13c3923`](https://github.com/geddy11/sysloss/commit/13c39236b0bbba27dd777dc70a71a08f693d187a))

### Features

- Add "loss" parameter to all loads, optionally configuring power as a loss
  ([`8168a26`](https://github.com/geddy11/sysloss/commit/8168a26583bd4afbedb020e808a6e1502089e09e))

- Add .rail_rep() method to System (voltage rail report)
  ([`92ec728`](https://github.com/geddy11/sysloss/commit/92ec7281437aaa4c1418e42703b9caa6355c8b79))

- Add group parameter to make_diag() function
  ([`1d8f9e4`](https://github.com/geddy11/sysloss/commit/1d8f9e4d94af37d66fb2caa48b4dab86c518121d))

- Add the option to add voltage rail names in System
  ([`a956ecb`](https://github.com/geddy11/sysloss/commit/a956ecbbe724f862cb546ed00907997b283d261d))

- Allow power rail name as parent parameter in add_comp(), change_comp()
  ([`6019576`](https://github.com/geddy11/sysloss/commit/6019576fd61e7f7652a82f5d42d80f337a5f7793))

### Refactoring

- Add check of limit values format
  ([`3136295`](https://github.com/geddy11/sysloss/commit/31362953fe3dfacc4210451831b04f59580f0c74))

- Create generic _solv_get_warns() method in Component class
  ([`4e2e8cc`](https://github.com/geddy11/sysloss/commit/4e2e8cc87708ee2da3c8d0b2091275246a2629e6))


## v1.6.0 (2024-10-31)

### Bug Fixes

- When saving system to .json, only include applicable limits for each component
  ([`fd5dea7`](https://github.com/geddy11/sysloss/commit/fd5dea76bfb9e03d18106f2c69992e7a12fd7419))

### Continuous Integration

- Add graphviz to rtd config
  ([`8fb1728`](https://github.com/geddy11/sysloss/commit/8fb1728f523243daa808063e6c6cf90dda831d31))

- Add sudo to graphviz install
  ([`20185f6`](https://github.com/geddy11/sysloss/commit/20185f6e94b00672bad6079fd369eeb2741be345))

- Fix Graphviz install
  ([`a46675b`](https://github.com/geddy11/sysloss/commit/a46675bdd63934b41d9dc4f70d7ecde5ad1f7935))

- Install Graphviz in ci step
  ([`eb026a2`](https://github.com/geddy11/sysloss/commit/eb026a2d8e73b1a08e5198ebdaf686cf772dabb6))

- Remove grayscull steps
  ([`553c2ed`](https://github.com/geddy11/sysloss/commit/553c2eda3537c314a1fec18522488c57037d0fcd))

### Documentation

- Update LinReg ground current parameter name in PCIe tutorial
  ([`b9da44b`](https://github.com/geddy11/sysloss/commit/b9da44b76a3b8feeae9cead7eae2758a36881c65))

### Features

- Add graphical power tree diagrams module
  ([`e3bb445`](https://github.com/geddy11/sysloss/commit/e3bb445587c0f1daf6c46b4b451c85943cfa0e77))

- Add group parameter in System, allowing grouping of components
  ([`83d9965`](https://github.com/geddy11/sysloss/commit/83d9965b9619d9d2748d9177dcbb07abdb81d91e))

### Refactoring

- Add generic component class
  ([`31873dd`](https://github.com/geddy11/sysloss/commit/31873dd3bf7dd3e320165aef00b7ce4e9071d215))

- Remove duplicate code in Components
  ([`488d451`](https://github.com/geddy11/sysloss/commit/488d4514117e2a35c962d845d55522380e9f4048))

- Use pydot in make_diagram() to support clusters (component groups)
  ([`6a53558`](https://github.com/geddy11/sysloss/commit/6a53558c52f3ee703d3f93837ec959d5819326d3))


## v1.5.0 (2024-10-14)

### Documentation

- Add limit definitions to component parameter files notebook.
  ([`9110379`](https://github.com/geddy11/sysloss/commit/91103796d71a9774dec148ad4fe32d99b330d224))

- Fix component parameter interpolation data dict examples in API
  ([`a0b9ed7`](https://github.com/geddy11/sysloss/commit/a0b9ed7e5be79a5095cfc2dd6af8102c13436d83))

- Update LinReg parameters in component files notebook
  ([`e65d5a9`](https://github.com/geddy11/sysloss/commit/e65d5a9ae7c4be045e5c1969371aa371f0c57610))

### Features

- Add method .limits() to system, which returns all user defined component limits
  ([`3dc8bf9`](https://github.com/geddy11/sysloss/commit/3dc8bf9aaa8550bfd2263692bf559b2873f2fe0e))

- Add power switch (PSwitch) component
  ([`8880ec1`](https://github.com/geddy11/sysloss/commit/8880ec1b46d0729f2dc92f816832afb0e236909a))

- New limit added: vd (voltage difference)
  ([`7e599b1`](https://github.com/geddy11/sysloss/commit/7e599b1778e52e5f047d4df1b7424631256db73c))

### Refactoring

- Add checking of sysLoss version when loading System from file
  ([`29eb5a4`](https://github.com/geddy11/sysloss/commit/29eb5a458d990a86eb629bd3cd5ba096333de296))

- Add state vector to solver parameters
  ([`f290f6d`](https://github.com/geddy11/sysloss/commit/f290f6d84251459a4434a227937e1a92b6df3485))

- Deprecate LinReg iq parameter, replace with ig
  ([`9183e37`](https://github.com/geddy11/sysloss/commit/9183e378dd1aef08a46ddd916ab7521339eb9214))

- Set state to off when phase in not active
  ([`bee1610`](https://github.com/geddy11/sysloss/commit/bee161044b916ac0aa22ab4b3665f4ebee2d38eb))


## v1.4.0 (2024-09-02)

### Bug Fixes

- **system**: Add check of component name and set default load phase in change_comp()
  ([`1a06e47`](https://github.com/geddy11/sysloss/commit/1a06e47ad14e694451f97f6b84f6587c319c0e38))

### Build System

- Fix CITATION.cff version update variable
  ([`298ea1c`](https://github.com/geddy11/sysloss/commit/298ea1cff2f758d6e1590ea1cb7fe73991082003))

### Continuous Integration

- Add codacy job
  ([`15bb292`](https://github.com/geddy11/sysloss/commit/15bb292aedc876a3cddb7448d2faa7df70507560))

- Add codacy token
  ([`532b850`](https://github.com/geddy11/sysloss/commit/532b850cbdafbba39f8ae4686f6f542293a0c93b))

- Switch to codacy github action
  ([`a5b758c`](https://github.com/geddy11/sysloss/commit/a5b758cdbf026d0416161930281c5588c7c81b4a))

### Documentation

- Add Codacy badge to README.md
  ([`2d09974`](https://github.com/geddy11/sysloss/commit/2d099744a29593478a0f5aa8548118dcea19ad07))

- Add examples to System class api
  ([`5f95963`](https://github.com/geddy11/sysloss/commit/5f95963f96df8cf783f4c3275a5e027adcb82b62))

- Add links to PyPI and Anaconda on badges
  ([`0ee0f96`](https://github.com/geddy11/sysloss/commit/0ee0f960047334ad868418e681b5694e8d49ab08))

- Explicit define default parameter values
  ([`47aa0f1`](https://github.com/geddy11/sysloss/commit/47aa0f17d04bee4abe79ce765a5eeb8b0c77ce71))

- Fix typos in battery life tutorial
  ([`fa36896`](https://github.com/geddy11/sysloss/commit/fa36896cb4a0e83f04f17c46ce3373c879c861ac))

- Update security.md
  ([`c3522d9`](https://github.com/geddy11/sysloss/commit/c3522d9bd840ff5238d19b7670d8cd7fdec2d908))

### Features

- Add ambient temperature (ta) as new parameter to .solve() and peak temperature (tp) as a new limit
  ([`2e74afe`](https://github.com/geddy11/sysloss/commit/2e74afe4eeca521a4f6f95e488b7ea9321eb4ca2))

If thermal resistance is specified on a component, peak temperature shows up as a new column in the
  results table. Peak temperature is calculated as ambient temperature plus temperature rise.


## v1.3.0 (2024-06-19)

### Build System

- Add PyPI classifiers
  ([`f8a0a9f`](https://github.com/geddy11/sysloss/commit/f8a0a9f26fc693f615a8218eb28939d516fac3c3))

### Continuous Integration

- Remove unused jobs in pipeline
  ([`4849845`](https://github.com/geddy11/sysloss/commit/48498455837e54bee43815c86cc31fd8a55f31de))

### Documentation

- Add anaconda badge to README.md
  ([`d9f08c1`](https://github.com/geddy11/sysloss/commit/d9f08c19485b2adeea57c74ba5c57fa883aa1f46))

- Add ROV battery pack tutorial
  ([`61afdba`](https://github.com/geddy11/sysloss/commit/61afdba5a2504ce609cc43737a80183a2251ca0f))

- Update sysLoss version in CITATION.cff
  ([`6fb8ad8`](https://github.com/geddy11/sysloss/commit/6fb8ad82a1943a4d8fe897b4244ac395e84d7476))

### Features

- Add tags argument to .batt_life()
  ([`495eea5`](https://github.com/geddy11/sysloss/commit/495eea53bdd45af605080e59814dab2828c91f38))

- Add thermal resistance parameter and temperature rise calculation
  ([`b8481a2`](https://github.com/geddy11/sysloss/commit/b8481a263065387e7cf600cda000be78cb307e0b))


## v1.2.0 (2024-05-27)

### Bug Fixes

- **system**: Add correct title to LinReg interpolation data plots
  ([`8ade81d`](https://github.com/geddy11/sysloss/commit/8ade81ddf9ef29387db89157b6da3feb850c5514))

### Continuous Integration

- Fix maintainer in conda receipe
  ([`1d27b0c`](https://github.com/geddy11/sysloss/commit/1d27b0c9c4f4411cf71c6efd29ffcecb38139e7c))

### Documentation

- Correct toml interpolation data format in "Component parameter files" page
  ([`9275463`](https://github.com/geddy11/sysloss/commit/92754635952bcecb1da80cc7739135b7aad43d64))

### Features

- Add power limits to all components (pi, po, pl)
  ([`ce36738`](https://github.com/geddy11/sysloss/commit/ce367382eda204f0a8961d65e2e13a173d34c83d))

- **components**: Add interpolation option to LinReg ground current parameter
  ([`2393767`](https://github.com/geddy11/sysloss/commit/23937677641ce6d99bbdb065b43a50a88a0a7a62))

### Refactoring

- System .params() method now gets component parameters from ._get_params() method
  ([`320fc09`](https://github.com/geddy11/sysloss/commit/320fc09d3ac5cd8a86f207ada78ddb73269dfa43))

- System method .plot_interp() gets figure annotations from component method ._get_annot()
  ([`bb2f017`](https://github.com/geddy11/sysloss/commit/bb2f0173ed8c8469a0bf166435c4f96bfd57fc64))


## v1.1.1 (2024-05-22)

### Bug Fixes

- Print tree in .tree() method to make it show in terminal mode
  ([`d2b43e3`](https://github.com/geddy11/sysloss/commit/d2b43e31fded161c4122b1bb61ed1486b2ee4818))

### Build System

- Add missing dependency of tqdm
  ([`4d01006`](https://github.com/geddy11/sysloss/commit/4d01006487db2e903231c230bca2ad64c19052d7))

- Fix dependency error
  ([`5d0e63f`](https://github.com/geddy11/sysloss/commit/5d0e63f51b6c9abf87a3bc842a437425c53ad604))

- Fix more dependency errors
  ([`6de316f`](https://github.com/geddy11/sysloss/commit/6de316f9b0e2c77be793bbdab1ee1e8558b85f1a))

- Relax package dependencies
  ([`33eb1b1`](https://github.com/geddy11/sysloss/commit/33eb1b1dbdd03d84c6ca241c313787c0f5828ebc))

- **docs**: Add ipywidgets to .readthedocs.yml
  ([`07d5273`](https://github.com/geddy11/sysloss/commit/07d52739272cc3aa595821c894880865c80a8486))

- **rtd**: Skip jupyter update
  ([`5f0a7f3`](https://github.com/geddy11/sysloss/commit/5f0a7f3347b6bbae020bd17fd45d6f9ba610eefc))

### Continuous Integration

- Change id in conda receipe
  ([`87513c3`](https://github.com/geddy11/sysloss/commit/87513c3b7cdba7ddb24ea9976534d2fa1607369b))

### Documentation

- Change DOI to "all versions" in README.md
  ([`1d354bc`](https://github.com/geddy11/sysloss/commit/1d354bc46d0d89d0c28534c8257cfd8eb74aaea9))

- Cleanup battery life notebook
  ([`2719bc5`](https://github.com/geddy11/sysloss/commit/2719bc5090a97e79d086f6e99fd68a8af5c328ea))

- Extend battery life notebook with new chapter on battery life optimization
  ([`230f4f4`](https://github.com/geddy11/sysloss/commit/230f4f4e92a83d5e7e00ac3f9e8b12bd1e12dd56))

- Hide output of cell in battery life notebook
  ([`d3b4778`](https://github.com/geddy11/sysloss/commit/d3b477872fdf4ab4aaf138b3fa7cc94fae204e6f))

- Hide output of cell in sensor daisy chain notebook
  ([`1cb8c0f`](https://github.com/geddy11/sysloss/commit/1cb8c0fe43f05234754397c0b83ee54e5e9f0e5a))

- Remove cell output in battery life notebook
  ([`120af8d`](https://github.com/geddy11/sysloss/commit/120af8d8d487d06201c798edda21d0cf5a752868))

- Remove output from import packages cell
  ([`0b56c35`](https://github.com/geddy11/sysloss/commit/0b56c35ae4d83552c9374302c33edaf3ea54f533))


## v1.1.0 (2024-05-08)

### Bug Fixes

- Relax python version requirement to 3.10
  ([`63acad9`](https://github.com/geddy11/sysloss/commit/63acad9c7d59c70534413ba676d056e7e9d6f405))

### Build System

- Fix semver version_variables name in pyproject.toml
  ([`76d1c72`](https://github.com/geddy11/sysloss/commit/76d1c727752d140cb0b97b0985651e40947537d2))

### Documentation

- Add battery life estimation tutorial
  ([`6b0243c`](https://github.com/geddy11/sysloss/commit/6b0243c8ee9ee1a4f7676e24790a3325ae7019f9))

- Add Zendo DOI to README.md
  ([`c19928d`](https://github.com/geddy11/sysloss/commit/c19928d77b6efc40a0c3c398f2c1d15cccf1f618))

### Features

- **system**: New method .batt_life() to estimate battery lifetime
  ([`b48d429`](https://github.com/geddy11/sysloss/commit/b48d429a07c43de899f326e3b724de5e86b4e181))


## v1.0.1 (2024-04-29)

### Bug Fixes

- Add __version__ to package
  ([`056c259`](https://github.com/geddy11/sysloss/commit/056c2593f93c453b18b0b962ca8500240f987bff))

### Build System

- **pypi**: Add links to repo and readthedocs
  ([`e838996`](https://github.com/geddy11/sysloss/commit/e8389968d83587140253b970cc2d756bccf20d4f))

- **rtd**: Add jupyter-book to config
  ([`c16bcc9`](https://github.com/geddy11/sysloss/commit/c16bcc91a90a336050451bddf55f657e66319511))

- **rtd**: Add more missing packages uses by sysLoss to rtd pipeline
  ([`c52c71b`](https://github.com/geddy11/sysloss/commit/c52c71b78957945a73b5bc48da8cd2e3a7f46a1a))

- **rtd**: Add sphinx-autoapi installation
  ([`fd30dc8`](https://github.com/geddy11/sysloss/commit/fd30dc8ba1124fee5da185333cc3c0083579f747))

- **rtd**: Add toml to build environment
  ([`a10be49`](https://github.com/geddy11/sysloss/commit/a10be49ef4b74cb4217e6a3299868355aeb28b8b))

### Documentation

- Change README.md image links to github
  ([`852ca43`](https://github.com/geddy11/sysloss/commit/852ca4381b367c9eebf9bf4cbcab1959c25e5c50))

- Rename code of conduct file
  ([`f8ce2bb`](https://github.com/geddy11/sysloss/commit/f8ce2bb3be5579a7b00519287efef30c627a7665))


## v1.0.0 (2024-04-24)

### Chores

- Move files from temporary project
  ([`9403a9d`](https://github.com/geddy11/sysloss/commit/9403a9dd346ae4d0a9dd337b216a6a641f9c5f25))

### Continuous Integration

- Disable coverage-badge
  ([`efcabaf`](https://github.com/geddy11/sysloss/commit/efcabaf47e6b38e9b49632667f73d35a1995bc7b))

- Disable coverage.xml in Codecov job
  ([`dff4eba`](https://github.com/geddy11/sysloss/commit/dff4ebac4ca61457d3ac58a5badca909e324ff08))

### Documentation

- Add coverage badge in README.md
  ([`0ba0962`](https://github.com/geddy11/sysloss/commit/0ba09623fe4323994c18187f7fb140f96fae59dc))
