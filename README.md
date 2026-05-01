# Cloud-init autoinstall builder

Web UI to build Ubuntu subiquity/autoinstall `#cloud-config` **user-data** and NoCloud **meta-data** from form fields.

## Paths and behavior

**`initial/`** (`~\Cloudinit_builder\initial`) supplies the default **user-data** / **meta-data** templates.

On startup, if **`backup/`** (`~\Cloudinit_builder\backup`) contains saved preferences, those override **`initial/`**; otherwise only **`initial/`** is used.

**Generate** writes fresh files to **`output/`** (`~\Cloudinit_builder\output`).

**NoCloud meta-data** in the builder is derived from **hostname** only (`instance-id` and `local-hostname`).

**Preferences file:** `~\Cloudinit_builder\backup\preferences.json`.

**Environment overrides:** `CLOUDINIT_INITIAL_DIR`, `CLOUDINIT_OUTPUT_DIR`, `CLOUDINIT_BACKUP_DIR`, `CLOUDINIT_PREFS_FILE`.

When you use those variables, the resolved directories replace the paths above.

## Setup and run

From the project root:

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install .
python app.py
```

Port and options are configured in `app.py` under `if __name__ == "__main__"`.

Once you have downloaded the files to a seed folder. 
```bash
 genisoimage -output seed.iso -volid cidata -joliet -r seed/
```