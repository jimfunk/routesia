import json
import nftables

from routesia.exceptions import NftablesException


class Nftables:
    def __init__(self):
        self.nft = nftables.Nftables()
        self.nft.set_json_output(True)

    def cmd(self, command):
        rc, output, error = self.nft.cmd(command)
        if rc != 0:
            raise NftablesException(f"Nftables command error: {error}")
        if output:
            return json.loads(output)
        return None
