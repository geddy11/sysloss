# CHANGELOG

## v1.3.0 (2024-06-19)

### Build

* build: add PyPI classifiers ([`f8a0a9f`](https://github.com/geddy11/sysloss/commit/f8a0a9f26fc693f615a8218eb28939d516fac3c3))

### Ci

* ci: remove unused jobs in pipeline ([`4849845`](https://github.com/geddy11/sysloss/commit/48498455837e54bee43815c86cc31fd8a55f31de))

### Documentation

* docs: update sysLoss version in CITATION.cff ([`6fb8ad8`](https://github.com/geddy11/sysloss/commit/6fb8ad82a1943a4d8fe897b4244ac395e84d7476))

* docs: add ROV battery pack tutorial ([`61afdba`](https://github.com/geddy11/sysloss/commit/61afdba5a2504ce609cc43737a80183a2251ca0f))

### Feature

* feat: add thermal resistance parameter and temperature rise calculation ([`b8481a2`](https://github.com/geddy11/sysloss/commit/b8481a263065387e7cf600cda000be78cb307e0b))

* feat: add tags argument to .batt_life() ([`495eea5`](https://github.com/geddy11/sysloss/commit/495eea53bdd45af605080e59814dab2828c91f38))

## v1.2.0 (2024-05-27)

### Ci

* ci: fix maintainer in conda receipe ([`1d27b0c`](https://github.com/geddy11/sysloss/commit/1d27b0c9c4f4411cf71c6efd29ffcecb38139e7c))

### Documentation

* docs: correct toml interpolation data format in &#34;Component parameter files&#34; page ([`9275463`](https://github.com/geddy11/sysloss/commit/92754635952bcecb1da80cc7739135b7aad43d64))

* docs: remove output from import packages cell ([`0b56c35`](https://github.com/geddy11/sysloss/commit/0b56c35ae4d83552c9374302c33edaf3ea54f533))

### Feature

* feat: add power limits to all components (pi, po, pl) ([`ce36738`](https://github.com/geddy11/sysloss/commit/ce367382eda204f0a8961d65e2e13a173d34c83d))

* feat(components): add interpolation option to LinReg ground current parameter ([`2393767`](https://github.com/geddy11/sysloss/commit/23937677641ce6d99bbdb065b43a50a88a0a7a62))

### Fix

* fix(system): add correct title to LinReg interpolation data plots ([`8ade81d`](https://github.com/geddy11/sysloss/commit/8ade81ddf9ef29387db89157b6da3feb850c5514))

### Refactor

* refactor: system .params() method now gets component parameters from ._get_params() method ([`320fc09`](https://github.com/geddy11/sysloss/commit/320fc09d3ac5cd8a86f207ada78ddb73269dfa43))

* refactor: system method .plot_interp() gets figure annotations from component method ._get_annot() ([`bb2f017`](https://github.com/geddy11/sysloss/commit/bb2f0173ed8c8469a0bf166435c4f96bfd57fc64))

### Unknown

* Merge branch &#39;main&#39; of https://github.com/geddy11/sysloss ([`ebce939`](https://github.com/geddy11/sysloss/commit/ebce93933ba42a73949a877dff8415091ce5490a))

## v1.1.1 (2024-05-22)

### Build

* build: relax package dependencies ([`33eb1b1`](https://github.com/geddy11/sysloss/commit/33eb1b1dbdd03d84c6ca241c313787c0f5828ebc))

* build: fix more dependency errors ([`6de316f`](https://github.com/geddy11/sysloss/commit/6de316f9b0e2c77be793bbdab1ee1e8558b85f1a))

* build: fix dependency error ([`5d0e63f`](https://github.com/geddy11/sysloss/commit/5d0e63f51b6c9abf87a3bc842a437425c53ad604))

* build: add missing dependency of tqdm ([`4d01006`](https://github.com/geddy11/sysloss/commit/4d01006487db2e903231c230bca2ad64c19052d7))

* build(rtd): skip jupyter update ([`5f0a7f3`](https://github.com/geddy11/sysloss/commit/5f0a7f3347b6bbae020bd17fd45d6f9ba610eefc))

* build(docs): add ipywidgets to .readthedocs.yml ([`07d5273`](https://github.com/geddy11/sysloss/commit/07d52739272cc3aa595821c894880865c80a8486))

### Ci

* ci: change id in conda receipe ([`87513c3`](https://github.com/geddy11/sysloss/commit/87513c3b7cdba7ddb24ea9976534d2fa1607369b))

### Documentation

* docs: extend battery life notebook with new chapter on battery life optimization ([`230f4f4`](https://github.com/geddy11/sysloss/commit/230f4f4e92a83d5e7e00ac3f9e8b12bd1e12dd56))

* docs: hide output of cell in sensor daisy chain notebook ([`1cb8c0f`](https://github.com/geddy11/sysloss/commit/1cb8c0fe43f05234754397c0b83ee54e5e9f0e5a))

* docs: change DOI to &#34;all versions&#34; in README.md ([`1d354bc`](https://github.com/geddy11/sysloss/commit/1d354bc46d0d89d0c28534c8257cfd8eb74aaea9))

* docs: remove cell output in battery life notebook ([`120af8d`](https://github.com/geddy11/sysloss/commit/120af8d8d487d06201c798edda21d0cf5a752868))

* docs: hide output of cell in battery life notebook ([`d3b4778`](https://github.com/geddy11/sysloss/commit/d3b477872fdf4ab4aaf138b3fa7cc94fae204e6f))

* docs: cleanup battery life notebook ([`2719bc5`](https://github.com/geddy11/sysloss/commit/2719bc5090a97e79d086f6e99fd68a8af5c328ea))

### Fix

* fix: print tree in .tree() method to make it show in terminal mode ([`d2b43e3`](https://github.com/geddy11/sysloss/commit/d2b43e31fded161c4122b1bb61ed1486b2ee4818))

## v1.1.0 (2024-05-08)

### Build

* build: fix semver version_variables name in pyproject.toml ([`76d1c72`](https://github.com/geddy11/sysloss/commit/76d1c727752d140cb0b97b0985651e40947537d2))

### Documentation

* docs: add battery life estimation tutorial ([`6b0243c`](https://github.com/geddy11/sysloss/commit/6b0243c8ee9ee1a4f7676e24790a3325ae7019f9))

* docs: add Zendo DOI to README.md ([`c19928d`](https://github.com/geddy11/sysloss/commit/c19928d77b6efc40a0c3c398f2c1d15cccf1f618))

### Feature

* feat(system): new method .batt_life() to estimate battery lifetime ([`b48d429`](https://github.com/geddy11/sysloss/commit/b48d429a07c43de899f326e3b724de5e86b4e181))

### Fix

* fix: relax python version requirement to 3.10 ([`63acad9`](https://github.com/geddy11/sysloss/commit/63acad9c7d59c70534413ba676d056e7e9d6f405))

### Unknown

* Merge pull request #5 from geddy11/battsim

Battery life estimation ([`1f999f8`](https://github.com/geddy11/sysloss/commit/1f999f81febf4712e6bcfc8d2917e3f241749281))

## v1.0.1 (2024-04-29)

### Build

* build(rtd): add more missing packages uses by sysLoss to rtd pipeline ([`c52c71b`](https://github.com/geddy11/sysloss/commit/c52c71b78957945a73b5bc48da8cd2e3a7f46a1a))

* build(rtd): add toml to build environment ([`a10be49`](https://github.com/geddy11/sysloss/commit/a10be49ef4b74cb4217e6a3299868355aeb28b8b))

* build(pypi): add links to repo and readthedocs ([`e838996`](https://github.com/geddy11/sysloss/commit/e8389968d83587140253b970cc2d756bccf20d4f))

* build(rtd): add sphinx-autoapi installation ([`fd30dc8`](https://github.com/geddy11/sysloss/commit/fd30dc8ba1124fee5da185333cc3c0083579f747))

* build(rtd): add jupyter-book to config ([`c16bcc9`](https://github.com/geddy11/sysloss/commit/c16bcc91a90a336050451bddf55f657e66319511))

### Documentation

* docs: rename code of conduct file ([`f8ce2bb`](https://github.com/geddy11/sysloss/commit/f8ce2bb3be5579a7b00519287efef30c627a7665))

* docs: change README.md image links to github ([`852ca43`](https://github.com/geddy11/sysloss/commit/852ca4381b367c9eebf9bf4cbcab1959c25e5c50))

### Fix

* fix: add __version__ to package ([`056c259`](https://github.com/geddy11/sysloss/commit/056c2593f93c453b18b0b962ca8500240f987bff))

### Unknown

* Update issue templates ([`ffaa63e`](https://github.com/geddy11/sysloss/commit/ffaa63eb0c96275318bfc5caaf743aa431fa79ca))

* Update issue templates ([`c3281ca`](https://github.com/geddy11/sysloss/commit/c3281ca6ea09812528b83b0f537925fc24e33e27))

* Merge pull request #4 from geddy11/pypi

docs: change image links in readme to absolute ([`bd60345`](https://github.com/geddy11/sysloss/commit/bd60345cb0f2f97bef563c5f236cd0deb98f2bdc))

* Merge pull request #3 from geddy11/rtd

build: fix readthedocs build ([`d738550`](https://github.com/geddy11/sysloss/commit/d73855035e6256706a9371e78534158ca27792f6))

## v1.0.0 (2024-04-24)

### Chore

* chore: move files from temporary project ([`9403a9d`](https://github.com/geddy11/sysloss/commit/9403a9dd346ae4d0a9dd337b216a6a641f9c5f25))

### Ci

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
