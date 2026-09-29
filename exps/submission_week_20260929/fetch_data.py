"""Fetch only pinned dataset files. Never download model weights or credentials."""
import hashlib
from pathlib import Path
import requests

HERE=Path(__file__).resolve().parent
FILES={
    'cuad_data.zip':('https://raw.githubusercontent.com/The-Atticus-Project/cuad/main/data.zip',
                     'f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a'),
    'docred_train_annotated.json.gz':('https://hf-mirror.com/datasets/thunlp/docred/resolve/main/data/train_annotated.json.gz',
                                    '0d01cd07cabd7f9077db6ea8628832cf60281b4228ec1ba54647f836a3b17d02'),
    'docred_dev.json.gz':('https://hf-mirror.com/datasets/thunlp/docred/resolve/main/data/dev.json.gz',
                        '6ae4d7f5b0b9d2cbe74b9634ed43b35b7cb5b7c0dc3a16226dbe343139a4ae05'),
    'docred_rel_info.json.gz':('https://hf-mirror.com/datasets/thunlp/docred/resolve/main/data/rel_info.json.gz',
                             '7ef27efff537ba89ae66f6f4e60e4908d4df3860a4c2819ea94fa5ed696bdc70'),
}


def fetch():
    dest=HERE/'sources';dest.mkdir(exist_ok=True)
    with requests.Session() as session:
        session.trust_env=False
        for name,(url,expected) in FILES.items():
            path=dest/name
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                    raise ValueError('Existing dataset hash mismatch: '+name)
                print(name,'verified cached');continue
            response=session.get(url,timeout=(15,90));response.raise_for_status()
            if hashlib.sha256(response.content).hexdigest()!=expected:
                raise ValueError('Downloaded dataset hash mismatch: '+name)
            temp=path.with_suffix(path.suffix+'.part');temp.write_bytes(response.content);temp.replace(path)
            print(name,'downloaded and verified')


if __name__=='__main__':fetch()
