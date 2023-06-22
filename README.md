# Unified File System

Developers face common problem in writing code in local filesystem first and then make the code to work with S3.
This creates a painful situation if not too much of code duplication.

Unified File System (`ufs`) package solves that problem where it exposes generic `File` and `Directory` classes.

Unified File System is an Object-Oriented way to work seamlessly between Posix and S3 filesystems

## Description

Usually we pass two different kinds of path parameter (Posix vs S3). And, we have to handle them differently either
using `os` or `boto3` python library.

With `ufs`, we have a wrapper classes like `PosixFile` / `S3File` (inherits from `File`)
and `PosixDirector` / `S3Directory` (inherits from `Directory`).

This makes writing functions and classes with a clear expectation to run with both Posix and S3 paths seamlessly.

## Installation

Install with pip:

``` bash
pip install ufs

```
