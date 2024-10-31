# CHANGELOG


## v1.6.0 (2024-10-31)

### Bug Fixes

* fix: when saving system to .json, only include applicable limits for each component ([`fd5dea7`](https://github.com/geddy11/sysloss/commit/fd5dea76bfb9e03d18106f2c69992e7a12fd7419))

### Continuous Integration

* ci: add sudo to graphviz install ([`20185f6`](https://github.com/geddy11/sysloss/commit/20185f6e94b00672bad6079fd369eeb2741be345))

* ci: fix Graphviz install ([`a46675b`](https://github.com/geddy11/sysloss/commit/a46675bdd63934b41d9dc4f70d7ecde5ad1f7935))

* ci: install Graphviz in ci step ([`eb026a2`](https://github.com/geddy11/sysloss/commit/eb026a2d8e73b1a08e5198ebdaf686cf772dabb6))

* ci: add graphviz to rtd config ([`8fb1728`](https://github.com/geddy11/sysloss/commit/8fb1728f523243daa808063e6c6cf90dda831d31))

* ci: remove grayscull steps ([`553c2ed`](https://github.com/geddy11/sysloss/commit/553c2eda3537c314a1fec18522488c57037d0fcd))

### Documentation

* docs: update LinReg ground current parameter name in PCIe tutorial ([`b9da44b`](https://github.com/geddy11/sysloss/commit/b9da44b76a3b8feeae9cead7eae2758a36881c65))

### Features

* feat: add group parameter in System, allowing grouping of components ([`83d9965`](https://github.com/geddy11/sysloss/commit/83d9965b9619d9d2748d9177dcbb07abdb81d91e))

* feat: add graphical power tree diagrams module ([`e3bb445`](https://github.com/geddy11/sysloss/commit/e3bb445587c0f1daf6c46b4b451c85943cfa0e77))

### Refactoring

* refactor: use pydot in make_diagram() to support clusters (component groups) ([`6a53558`](https://github.com/geddy11/sysloss/commit/6a53558c52f3ee703d3f93837ec959d5819326d3))

* refactor: remove duplicate code in Components ([`488d451`](https://github.com/geddy11/sysloss/commit/488d4514117e2a35c962d845d55522380e9f4048))

* refactor: add generic component class ([`31873dd`](https://github.com/geddy11/sysloss/commit/31873dd3bf7dd3e320165aef00b7ce4e9071d215))


## v1.5.0 (2024-10-14)

### Documentation

* docs: update LinReg parameters in component files notebook ([`e65d5a9`](https://github.com/geddy11/sysloss/commit/e65d5a9ae7c4be045e5c1969371aa371f0c57610))

* docs: fix component parameter interpolation data dict examples in API ([`a0b9ed7`](https://github.com/geddy11/sysloss/commit/a0b9ed7e5be79a5095cfc2dd6af8102c13436d83))

* docs: add limit definitions to component parameter files notebook. ([`9110379`](https://github.com/geddy11/sysloss/commit/91103796d71a9774dec148ad4fe32d99b330d224))

### Features

* feat: add power switch (PSwitch) component ([`8880ec1`](https://github.com/geddy11/sysloss/commit/8880ec1b46d0729f2dc92f816832afb0e236909a))

* feat: new limit added: vd (voltage difference) ([`7e599b1`](https://github.com/geddy11/sysloss/commit/7e599b1778e52e5f047d4df1b7424631256db73c))

* feat: add method .limits() to system, which returns all user defined component limits ([`3dc8bf9`](https://github.com/geddy11/sysloss/commit/3dc8bf9aaa8550bfd2263692bf559b2873f2fe0e))

### Refactoring

* refactor: deprecate LinReg iq parameter, replace with ig ([`9183e37`](https://github.com/geddy11/sysloss/commit/9183e378dd1aef08a46ddd916ab7521339eb9214))

* refactor: add checking of sysLoss version when loading System from file ([`29eb5a4`](https://github.com/geddy11/sysloss/commit/29eb5a458d990a86eb629bd3cd5ba096333de296))

* refactor: set state to off when phase in not active ([`bee1610`](https://github.com/geddy11/sysloss/commit/bee161044b916ac0aa22ab4b3665f4ebee2d38eb))

* refactor: add state vector to solver parameters ([`f290f6d`](https://github.com/geddy11/sysloss/commit/f290f6d84251459a4434a227937e1a92b6df3485))


## v1.4.0 (2024-09-02)

### Bug Fixes

* fix(system): add check of component name and set default load phase in change_comp() ([`1a06e47`](https://github.com/geddy11/sysloss/commit/1a06e47ad14e694451f97f6b84f6587c319c0e38))

### Build System

* build: fix CITATION.cff version update variable ([`298ea1c`](https://github.com/geddy11/sysloss/commit/298ea1cff2f758d6e1590ea1cb7fe73991082003))

### Continuous Integration

* ci: switch to codacy github action ([`a5b758c`](https://github.com/geddy11/sysloss/commit/a5b758cdbf026d0416161930281c5588c7c81b4a))

* ci: add codacy token ([`532b850`](https://github.com/geddy11/sysloss/commit/532b850cbdafbba39f8ae4686f6f542293a0c93b))

* ci: add codacy job ([`15bb292`](https://github.com/geddy11/sysloss/commit/15bb292aedc876a3cddb7448d2faa7df70507560))

### Documentation

* docs: fix typos in battery life tutorial ([`fa36896`](https://github.com/geddy11/sysloss/commit/fa36896cb4a0e83f04f17c46ce3373c879c861ac))

* docs: add links to PyPI and Anaconda on badges ([`0ee0f96`](https://github.com/geddy11/sysloss/commit/0ee0f960047334ad868418e681b5694e8d49ab08))

* docs: add Codacy badge to README.md ([`2d09974`](https://github.com/geddy11/sysloss/commit/2d099744a29593478a0f5aa8548118dcea19ad07))

* docs: add examples to System class api ([`5f95963`](https://github.com/geddy11/sysloss/commit/5f95963f96df8cf783f4c3275a5e027adcb82b62))

* docs: explicit define default parameter values ([`47aa0f1`](https://github.com/geddy11/sysloss/commit/47aa0f17d04bee4abe79ce765a5eeb8b0c77ce71))

* docs: update security.md ([`c3522d9`](https://github.com/geddy11/sysloss/commit/c3522d9bd840ff5238d19b7670d8cd7fdec2d908))

### Features

* feat: add ambient temperature (ta) as new parameter to .solve() and peak temperature (tp) as a new limit

If thermal resistance is specified on a component, peak temperature shows up as a new column in the results table. Peak temperature is calculated as ambient temperature plus temperature rise. ([`2e74afe`](https://github.com/geddy11/sysloss/commit/2e74afe4eeca521a4f6f95e488b7ea9321eb4ca2))

### Unknown

* Create SECURITY.md ([`94145e2`](https://github.com/geddy11/sysloss/commit/94145e24eeacc918f0582f78e68eab6384fde62e))

* Merge branch 'main' of https://github.com/geddy11/sysloss ([`26227ac`](https://github.com/geddy11/sysloss/commit/26227acab51e7e1ff459fe512319293974198d4d))


## v1.3.0 (2024-06-19)

### Build System

* build: add PyPI classifiers ([`f8a0a9f`](https://github.com/geddy11/sysloss/commit/f8a0a9f26fc693f615a8218eb28939d516fac3c3))

### Continuous Integration

* ci: remove unused jobs in pipeline ([`4849845`](https://github.com/geddy11/sysloss/commit/48498455837e54bee43815c86cc31fd8a55f31de))

### Documentation

* docs: add anaconda badge to README.md ([`d9f08c1`](https://github.com/geddy11/sysloss/commit/d9f08c19485b2adeea57c74ba5c57fa883aa1f46))

* docs: update sysLoss version in CITATION.cff ([`6fb8ad8`](https://github.com/geddy11/sysloss/commit/6fb8ad82a1943a4d8fe897b4244ac395e84d7476))

* docs: add ROV battery pack tutorial ([`61afdba`](https://github.com/geddy11/sysloss/commit/61afdba5a2504ce609cc43737a80183a2251ca0f))

### Features

* feat: add thermal resistance parameter and temperature rise calculation ([`b8481a2`](https://github.com/geddy11/sysloss/commit/b8481a263065387e7cf600cda000be78cb307e0b))

* feat: add tags argument to .batt_life() ([`495eea5`](https://github.com/geddy11/sysloss/commit/495eea53bdd45af605080e59814dab2828c91f38))


## v1.2.0 (2024-05-27)

### Bug Fixes

* fix(system): add correct title to LinReg interpolation data plots ([`8ade81d`](https://github.com/geddy11/sysloss/commit/8ade81ddf9ef29387db89157b6da3feb850c5514))

### Continuous Integration

* ci: fix maintainer in conda receipe ([`1d27b0c`](https://github.com/geddy11/sysloss/commit/1d27b0c9c4f4411cf71c6efd29ffcecb38139e7c))

### Documentation

* docs: correct toml interpolation data format in "Component parameter files" page ([`9275463`](https://github.com/geddy11/sysloss/commit/92754635952bcecb1da80cc7739135b7aad43d64))

### Features

* feat: add power limits to all components (pi, po, pl) ([`ce36738`](https://github.com/geddy11/sysloss/commit/ce367382eda204f0a8961d65e2e13a173d34c83d))

* feat(components): add interpolation option to LinReg ground current parameter ([`2393767`](https://github.com/geddy11/sysloss/commit/23937677641ce6d99bbdb065b43a50a88a0a7a62))

### Refactoring

* refactor: system .params() method now gets component parameters from ._get_params() method ([`320fc09`](https://github.com/geddy11/sysloss/commit/320fc09d3ac5cd8a86f207ada78ddb73269dfa43))

* refactor: system method .plot_interp() gets figure annotations from component method ._get_annot() ([`bb2f017`](https://github.com/geddy11/sysloss/commit/bb2f0173ed8c8469a0bf166435c4f96bfd57fc64))

### Unknown

* Merge branch 'main' of https://github.com/geddy11/sysloss ([`ebce939`](https://github.com/geddy11/sysloss/commit/ebce93933ba42a73949a877dff8415091ce5490a))


## v1.1.1 (2024-05-22)

### Bug Fixes

* fix: print tree in .tree() method to make it show in terminal mode ([`d2b43e3`](https://github.com/geddy11/sysloss/commit/d2b43e31fded161c4122b1bb61ed1486b2ee4818))

### Build System

* build: relax package dependencies ([`33eb1b1`](https://github.com/geddy11/sysloss/commit/33eb1b1dbdd03d84c6ca241c313787c0f5828ebc))

* build: fix more dependency errors ([`6de316f`](https://github.com/geddy11/sysloss/commit/6de316f9b0e2c77be793bbdab1ee1e8558b85f1a))

* build: fix dependency error ([`5d0e63f`](https://github.com/geddy11/sysloss/commit/5d0e63f51b6c9abf87a3bc842a437425c53ad604))

* build: add missing dependency of tqdm ([`4d01006`](https://github.com/geddy11/sysloss/commit/4d01006487db2e903231c230bca2ad64c19052d7))

* build(rtd): skip jupyter update ([`5f0a7f3`](https://github.com/geddy11/sysloss/commit/5f0a7f3347b6bbae020bd17fd45d6f9ba610eefc))

* build(docs): add ipywidgets to .readthedocs.yml ([`07d5273`](https://github.com/geddy11/sysloss/commit/07d52739272cc3aa595821c894880865c80a8486))

### Continuous Integration

* ci: change id in conda receipe ([`87513c3`](https://github.com/geddy11/sysloss/commit/87513c3b7cdba7ddb24ea9976534d2fa1607369b))

### Documentation

* docs: remove output from import packages cell ([`0b56c35`](https://github.com/geddy11/sysloss/commit/0b56c35ae4d83552c9374302c33edaf3ea54f533))

* docs: extend battery life notebook with new chapter on battery life optimization ([`230f4f4`](https://github.com/geddy11/sysloss/commit/230f4f4e92a83d5e7e00ac3f9e8b12bd1e12dd56))

* docs: hide output of cell in sensor daisy chain notebook ([`1cb8c0f`](https://github.com/geddy11/sysloss/commit/1cb8c0fe43f05234754397c0b83ee54e5e9f0e5a))

* docs: change DOI to "all versions" in README.md ([`1d354bc`](https://github.com/geddy11/sysloss/commit/1d354bc46d0d89d0c28534c8257cfd8eb74aaea9))

* docs: remove cell output in battery life notebook ([`120af8d`](https://github.com/geddy11/sysloss/commit/120af8d8d487d06201c798edda21d0cf5a752868))

* docs: hide output of cell in battery life notebook ([`d3b4778`](https://github.com/geddy11/sysloss/commit/d3b477872fdf4ab4aaf138b3fa7cc94fae204e6f))

* docs: cleanup battery life notebook ([`2719bc5`](https://github.com/geddy11/sysloss/commit/2719bc5090a97e79d086f6e99fd68a8af5c328ea))


## v1.1.0 (2024-05-08)

### Bug Fixes

* fix: relax python version requirement to 3.10 ([`63acad9`](https://github.com/geddy11/sysloss/commit/63acad9c7d59c70534413ba676d056e7e9d6f405))

### Build System

* build: fix semver version_variables name in pyproject.toml ([`76d1c72`](https://github.com/geddy11/sysloss/commit/76d1c727752d140cb0b97b0985651e40947537d2))

### Documentation

* docs: add battery life estimation tutorial ([`6b0243c`](https://github.com/geddy11/sysloss/commit/6b0243c8ee9ee1a4f7676e24790a3325ae7019f9))

* docs: add Zendo DOI to README.md ([`c19928d`](https://github.com/geddy11/sysloss/commit/c19928d77b6efc40a0c3c398f2c1d15cccf1f618))

### Features

* feat(system): new method .batt_life() to estimate battery lifetime ([`b48d429`](https://github.com/geddy11/sysloss/commit/b48d429a07c43de899f326e3b724de5e86b4e181))

### Unknown

* Merge pull request #5 from geddy11/battsim

Battery life estimation ([`1f999f8`](https://github.com/geddy11/sysloss/commit/1f999f81febf4712e6bcfc8d2917e3f241749281))


## v1.0.1 (2024-04-29)

### Bug Fixes

* fix: add __version__ to package ([`056c259`](https://github.com/geddy11/sysloss/commit/056c2593f93c453b18b0b962ca8500240f987bff))

### Build System

* build(rtd): add more missing packages uses by sysLoss to rtd pipeline ([`c52c71b`](https://github.com/geddy11/sysloss/commit/c52c71b78957945a73b5bc48da8cd2e3a7f46a1a))

* build(rtd): add toml to build environment ([`a10be49`](https://github.com/geddy11/sysloss/commit/a10be49ef4b74cb4217e6a3299868355aeb28b8b))

* build(pypi): add links to repo and readthedocs ([`e838996`](https://github.com/geddy11/sysloss/commit/e8389968d83587140253b970cc2d756bccf20d4f))

* build(rtd): add sphinx-autoapi installation ([`fd30dc8`](https://github.com/geddy11/sysloss/commit/fd30dc8ba1124fee5da185333cc3c0083579f747))

* build(rtd): add jupyter-book to config ([`c16bcc9`](https://github.com/geddy11/sysloss/commit/c16bcc91a90a336050451bddf55f657e66319511))

### Documentation

* docs: rename code of conduct file ([`f8ce2bb`](https://github.com/geddy11/sysloss/commit/f8ce2bb3be5579a7b00519287efef30c627a7665))

* docs: change README.md image links to github ([`852ca43`](https://github.com/geddy11/sysloss/commit/852ca4381b367c9eebf9bf4cbcab1959c25e5c50))

### Unknown

* Update issue templates ([`ffaa63e`](https://github.com/geddy11/sysloss/commit/ffaa63eb0c96275318bfc5caaf743aa431fa79ca))

* Update issue templates ([`c3281ca`](https://github.com/geddy11/sysloss/commit/c3281ca6ea09812528b83b0f537925fc24e33e27))

* Merge pull request #4 from geddy11/pypi

docs: change image links in readme to absolute ([`bd60345`](https://github.com/geddy11/sysloss/commit/bd60345cb0f2f97bef563c5f236cd0deb98f2bdc))

* Merge pull request #3 from geddy11/rtd

build: fix readthedocs build ([`d738550`](https://github.com/geddy11/sysloss/commit/d73855035e6256706a9371e78534158ca27792f6))


## v1.0.0 (2024-04-24)

### Chores

* chore: move files from temporary project ([`9403a9d`](https://github.com/geddy11/sysloss/commit/9403a9dd346ae4d0a9dd337b216a6a641f9c5f25))

### Continuous Integration

* ci: disable coverage-badge ([`efcabaf`](https://github.com/geddy11/sysloss/commit/efcabaf47e6b38e9b49632667f73d35a1995bc7b))

* ci: disable coverage.xml in Codecov job ([`dff4eba`](https://github.com/geddy11/sysloss/commit/dff4ebac4ca61457d3ac58a5badca909e324ff08))

### Documentation

* docs: add coverage badge in README.md ([`0ba0962`](https://github.com/geddy11/sysloss/commit/0ba09623fe4323994c18187f7fb140f96fae59dc))

### Unknown

* Merge pull request #2 from geddy11/fix_ci

docs: add coverage badge in README.md ([`17d47c8`](https://github.com/geddy11/sysloss/commit/17d47c823669ccaa9959be726d430acae7c45e62))

* Merge pull request #1 from geddy11/update

chore: transfer files from temporary project ([`d6279db`](https://github.com/geddy11/sysloss/commit/d6279db3fe55b3072a645b4681b86b455e8cc1ee))

* Initial packet structure ([`3a243bd`](https://github.com/geddy11/sysloss/commit/3a243bd7c617e4ed0ecac821ed63eba6d17b69b6))

* Update README.md ([`9fb4d2e`](https://github.com/geddy11/sysloss/commit/9fb4d2e6efe4b9ef133ff1e79be54eb8ce71a551))

* Initial commit ([`963d38b`](https://github.com/geddy11/sysloss/commit/963d38bc8f85442d6dd32522bda98714ffa77055))
