# Spikes

One folder per spike, `spikes/<name>/`, worked on in branch `spike/<name>`.

Keep each spike self-contained, with its own build or project file (and
lockfile, if your language uses one) rather than adding it to a shared build.
That way one broken spike can't stop the others building.

## Using Code From the Original Repo

Reference the original repo rather than copying from it. Read and build it,
but never edit it. These examples assume the original repo is checked out next
to the spike repo, as `@PROJECT@/`, so a spike in `spikes/<name>/` reaches it at
`../../../@PROJECT@/`.

Rust, in `Cargo.toml`:

```toml
some-crate = { path = "../../../@PROJECT@/crates/some-crate" }
```

Node, in `package.json`:

```json
"some-lib": "file:../../../@PROJECT@/packages/some-lib"
```

C or C++, in `CMakeLists.txt`:

```cmake
add_subdirectory(../../../@PROJECT@/libs/some-lib some-lib)
```
