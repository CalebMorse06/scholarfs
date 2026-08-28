# Connector state

ScholarFS core does not run connectors or hold credentials. External connectors write a normalized deadline-import file, which you preview and apply with `scholarfs deadline import`.

Local cursors and connector state belong in this ignored directory. Keep tokens in environment variables or the operating system credential store.

