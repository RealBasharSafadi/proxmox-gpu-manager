import os
import subprocess
import json
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from proxmoxer import ProxmoxAPI

# Initialize Rich Console
console = Console()

# Automatically detect Proxmox IP
PROXMOX_HOST = subprocess.getoutput("hostname -I | awk '{print $1}'").strip()
PROXMOX_USER = "root@pam"
PROXMOX_PASSWORD = "your-password"  # This should be securely handled
CONFIG_FILE = "/opt/proxmox-gpu-manager/gpu_manager_config.json"

def check_dependencies():
    dependencies = ["python3", "pip3", "git", "python3-rich", "python3-proxmoxer"]
    for dep in dependencies:
        if subprocess.call(["dpkg", "-s", dep], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            console.print(f"[bold red]{dep} is missing. Installing...[/bold red]")
            os.system(f"apt install {dep} -y")

check_dependencies()

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def list_gpus():
    try:
        output = subprocess.getoutput("lspci -nn | grep -i 'VGA\\|3D'")
        gpus = [line.strip() for line in output.split("\\n") if line]
        return gpus
    except subprocess.CalledProcessError:
        return []

def list_vms():
    proxmox = ProxmoxAPI(PROXMOX_HOST, user=PROXMOX_USER, password=PROXMOX_PASSWORD, verify_ssl=False)
    return proxmox.nodes("pve").qemu.get()

def assign_gpu(vmid, pci_id):
    conf_path = f"/etc/pve/qemu-server/{vmid}.conf"
    if validate_pci_id(pci_id):
        with open(conf_path, "a") as f:
            f.write(f"\\nhostpci0: {pci_id},pcie=1\\n")
        os.system(f"qm set {vmid} --hostpci0 {pci_id},pcie=1")
        console.print(f"[bold green]GPU {pci_id} assigned to VM {vmid}.[/bold green]")

def remove_gpu(vmid):
    conf_path = f"/etc/pve/qemu-server/{vmid}.conf"
    if os.path.exists(conf_path) and "hostpci0" in open(conf_path).read():
        os.system(f"qm set {vmid} --delete hostpci0")
        console.print(f"[bold red]GPU removed from VM {vmid}.[/bold red]")
    else:
        console.print(f"[yellow]No GPU assigned to VM {vmid}.[/yellow]")

def validate_pci_id(pci_id):
    output = subprocess.getoutput("lspci -nn")
    if pci_id not in output:
        console.print("[red]Invalid PCI ID![/red]")
        return False
    return True

def unbind_gpu(pci_id):
    if validate_pci_id(pci_id):
        os.system(f"echo {pci_id} > /sys/bus/pci/devices/{pci_id}/driver/unbind")
        os.system("modprobe vfio-pci")
        os.system(f"echo {pci_id} > /sys/bus/pci/drivers/vfio-pci/bind")
        console.print(f"[bold yellow]GPU {pci_id} unbound and assigned to vfio-pci.[/bold yellow]")

def check_nvidia_driver():
    if subprocess.call("which nvidia-smi", shell=True) != 0:
        console.print("[red]NVIDIA driver is missing! Install it before using monitoring.[/red]")
        return False
    return True

def monitor_gpus():
    if check_nvidia_driver():
        os.system("nvidia-smi")

def main_menu():
    while True:
        table = Table(title="Proxmox GPU Passthrough Manager")
        table.add_column("Option", style="cyan")
        table.add_column("Action", style="magenta")
        table.add_row("1", "List available GPUs")
        table.add_row("2", "List Proxmox VMs")
        table.add_row("3", "Assign GPU to VM")
        table.add_row("4", "Remove GPU from VM")
        table.add_row("5", "Unbind GPU from Host")
        table.add_row("6", "Monitor GPU Usage")
        table.add_row("7", "Exit")
        console.print(table)
        choice = Prompt.ask("Select an option")

        if choice == "1":
            gpus = list_gpus()
            console.print("[bold blue]Available GPUs:[/bold blue]", gpus)
        elif choice == "2":
            vms = list_vms()
            console.print("[bold blue]Available VMs:[/bold blue]")
            for vm in vms:
                console.print(f"[green]VM ID: {vm['vmid']} - {vm['name']} (Status: {vm['status']})[/green]")
        elif choice == "3":
            vmid = Prompt.ask("Enter VM ID")
            pci_id = Prompt.ask("Enter GPU PCI ID")
            assign_gpu(vmid, pci_id)
        elif choice == "4":
            vmid = Prompt.ask("Enter VM ID")
            remove_gpu(vmid)
        elif choice == "5":
            pci_id = Prompt.ask("Enter GPU PCI ID")
            unbind_gpu(pci_id)
        elif choice == "6":
            monitor_gpus()
        elif choice == "7":
            console.print("[bold red]Exiting...[/bold red]")
            break
        else:
            console.print("[bold red]Invalid option. Try again.[/bold red]")

if __name__ == "__main__":
    main_menu()
