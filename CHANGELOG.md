# Changelog

<!--next-version-placeholder-->

## v0.3.5 (2024-03-20)

### Fix

* Require 'black' as a dependency ([`3cf51d3`](https://github.com/robinvandernoord/pydal2sql-core/commit/3cf51d3894e90ddd5ea6677c4fdb70a1b03a364b))

## v0.3.4 (2023-12-05)

### Fix

* Sqlite:memory is now mapped to sqlite dialect ([`3aa4666`](https://github.com/robinvandernoord/pydal2sql-core/commit/3aa466602e6acb771fb63189f74cfa8eaaf398f0))
* **typedal:** TypeDAL 2.2 fix ([`2f2f3e4`](https://github.com/robinvandernoord/pydal2sql-core/commit/2f2f3e446bb714df9d86f8f5b525aeac8cb8dd3d))

## v0.3.3 (2023-11-20)

### Fix

* Don't `create` on `alter` fail automatically, let the user decide ([`2fbc3cc`](https://github.com/robinvandernoord/pydal2sql-core/commit/2fbc3cc0fe085a7aeec466c4f6fb3ce82e96fd72))

## v0.3.2 (2023-11-20)

### Fix

* **create:** Migrations are now printed in the same order the tables are defined ([`ad2b1f8`](https://github.com/robinvandernoord/pydal2sql-core/commit/ad2b1f8e281f425baee1fb2efec84f0850f5c307))

## v0.3.1 (2023-11-20)

### Fix

* Use `--output-file -` will print to stdout ([`e49a7ac`](https://github.com/robinvandernoord/pydal2sql-core/commit/e49a7ac171089fb4c06c38d7eebdff2eda49f8cf))
* Don't write empty migrations ([`c2cb33e`](https://github.com/robinvandernoord/pydal2sql-core/commit/c2cb33ede1db6de95261aa361c66d9e992b0219b))

## v0.3.0 (2023-11-20)

### Feature

* Prevent duplicate migrations in edwh-migrate format ([`1592173`](https://github.com/robinvandernoord/pydal2sql-core/commit/1592173f91dd5ccfab49137ce345dddc44c1fa90))

## v0.2.0 (2023-11-17)

### Feature

* Use a dummy DAL in order to prevent queries actually being executed on a database ([`14c3bfd`](https://github.com/robinvandernoord/pydal2sql-core/commit/14c3bfd94b9953758f0c876e33c76be0fedf3102))
* Allow different output format (edwh-migrate) + output file ([`d2b214f`](https://github.com/robinvandernoord/pydal2sql-core/commit/d2b214f6fbde1970c24dab58c74328ee014efec7))
* Expose core_ and handle_cli methods from the top level of the library ([`6f41d47`](https://github.com/robinvandernoord/pydal2sql-core/commit/6f41d47a0fe3e267d374211eb3591782424a73f2))
* Move core create and alter functionality to this library ([`3f3a260`](https://github.com/robinvandernoord/pydal2sql-core/commit/3f3a260f89bc9c57d83e529fef7920a9faa59349))

### Fix

* Make all checks pass, including pytest 100% cov ([`d0bea7e`](https://github.com/robinvandernoord/pydal2sql-core/commit/d0bea7eadf14c22375682070806001f8a125596d))
* **edwh-migrate:** Multiple migrations are now split up into multiple migrate functions ([`c6839a5`](https://github.com/robinvandernoord/pydal2sql-core/commit/c6839a53f4597baa25703ada537f56ddadc3fd53))
* After trying `create` on alter fail, suppress exceptions and return False if it fails ([`a2d68c5`](https://github.com/robinvandernoord/pydal2sql-core/commit/a2d68c57e3181d4d22efa2e24d8ebf9dc2eccd24))
* Use proper dialect of the selected db type instead of plain SQL ([`76835a7`](https://github.com/robinvandernoord/pydal2sql-core/commit/76835a71cec931b59d121397fc73d99d3395089d))
* Support TypeDAL in addition to pydal ([`b0cbc11`](https://github.com/robinvandernoord/pydal2sql-core/commit/b0cbc117da165bf68b40df9af2eb436d741cc59b))

### Documentation

* Added todo ([`e18091e`](https://github.com/robinvandernoord/pydal2sql-core/commit/e18091ed844e121cbe7b46f94c26174785549a03))

## v0.1.1 (2023-07-31)
### Fix
* Replaced reference to pydal2sql to pydal2sql_core ([`45cd339`](https://github.com/robinvandernoord/pydal2sql-core/commit/45cd339b56c32a928a4b0ac5eb7746c7a905be71))

## v0.1.0 (2023-07-31)

### Feature

* Split pydal2sql core functionality from main (cli) package. ([`ae70d4d`](https://github.com/robinvandernoord/pydal2sql-core/commit/ae70d4d1f755f09c6db80c42c1806984c9a7ad25))

### Fix

* --function should now also work for ALTER (in addition to CREATE) ([`02cc8da`](https://github.com/robinvandernoord/pydal2sql-core/commit/02cc8dafc002db10e1e05a55a6e9664c59d0aac1))
* Moved magic to `witchery` package and WIP on more pytests ([`071fc0d`](https://github.com/robinvandernoord/pydal2sql-core/commit/071fc0d10039cec9fd777880c611f3b8ad12f027))

### Documentation

* Updated readme ([`170ad53`](https://github.com/robinvandernoord/pydal2sql-core/commit/170ad53d66f521263dca7715f12000bb3b458e92))
