# File descriptors and pipelines

- A process starts with standard input, output, and error as descriptors 0, 1, and 2.
- `dup2` changes which open file a descriptor refers to.
- After `fork`, the parent and child have separate descriptor tables pointing at the same open-file descriptions.
- Pipeline debugging question: which process still holds each read or write end open?

## Still unclear

- Why a reader can wait forever when an unrelated process retains the pipe's write end.

