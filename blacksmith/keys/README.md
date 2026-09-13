# Trusted minisign public keys

Place official publisher `*.pub` files in this directory. They ship with the
package and are always tried when `--require-signature` is set.

Generate a keypair (do not commit the secret key):

```bash
minisign -G -p jimididit.pub -s jimididit.key
```

Commit only the `.pub` file here. Keep `.key` offline.

Users can also add keys under the user trust directory (see README) or pass
`--pubkey PATH` for a one-off verification.
