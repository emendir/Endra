# Endra

A fully distributed, no-servers, peer-to-peer encrypted messaging protocol.

See the EndraApp project for a GUI messaging application for desktop and mobile implementing Endra.

## Features

- fully peer to peer, no servers of any kind
- can work independently of the internet
- full end-to-end encryption
- ephemeral cryptography
- multiple devices per profile (i.e. user account)
- multiple profiles per device
- application for desktop and mobile (tested on Linux (Ubuntu x86-64) and Android (arm-64))
- can be used as a library for embedding into other applications
- implements W3C's DID standard
- will become part of an expandable ecosystem incl. calendar and file-sharing

### Disadvantages

- higher resource usage on user devices compared to conventional messengers

## Endra's Tech Stacks

| Layer              | Data Features                                             | Networking Features                                                |
| ------------------ | --------------------------------------------------------- | ------------------------------------------------------------------ |
| Endra              | - organisation of identities, contacts & chats            | - instant messaging                                                |
| Walytis-Mutability | - mutable blocks (for editable messages)                  |                                                                    |
| Walytis-Offchain   | - private encrypted blocks<br>- contact authentication    | - communication encryption & authentication for Walytis-Identities |
| Walytis-Identities | - identities, cryptographic key management                | - multi-device identities<br>- cryptographic key management        |
| Walytis            | - new blocks notification<br>- data integrity maintenance |                                                                    |
| IPFS/libp2p        | - file sharing                                            | - persistent addressing<br>- p2p routing<br>- NAT-hole-punching    |

- **Endra:** a fully distributed, peer-to-peer encrypted messaging protocol, built on Walytis and its blockchain-overlays
- **Walytis-Identities, Walytis-Offchain, Walytis-Mutability:** blockchain-overlays - systems providing an interface with additional features to Walytis databases
- **Walytis:** a database blockchain - a lightweight, non-linear & flexible blockchain for distributed databases, built on IPFS
- **IPFS:** Interplanetary File System - peer-to-peer file-sharing, built on libp2p
- **libp2p:** a peer-to-peer OSI layer 4 communications protocol, on overlay over the internet protocol

## Project Status **EXPERIMENTAL**

This library is very early in its development.

The API of this library IS LIKELY TO CHANGE in the near future!
