import json
import nftables


class NftablesException(Exception):
    pass


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

    def get_ruleset(self):
        tables = {}
        items = self.cmd("list ruleset")
        for item in items["nftables"]:
            if "metainfo" in item:
                continue
            elif "table" in item:
                table = item["table"]
                if table["family"] not in tables:
                    tables[table["family"]] = {}
                table["chains"] = {}
                tables[table["family"]][table["name"]] = table
            elif "chain" in item:
                chain = item["chain"]
                table = tables[chain["family"]][chain["table"]]
                chain["rules"] = []
                table["chains"][chain["name"]] = chain
            elif "rule" in item:
                rule = item["rule"]
                chain = tables[rule["family"]][rule["table"]]["chains"][rule["chain"]]
                chain["rules"].append(rule)
            else:
                type = list(item.keys())[0]
                raise NftablesException(f"Unknown item type {type}")

        return tables
