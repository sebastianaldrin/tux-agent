"""
TuxAgent Extension Manager
Install, remove, and manage TuxAgent extensions
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

# Extension registry - defines all available extensions
EXTENSIONS = {
    "nautilus": {
        "name": "Nautilus Integration",
        "description": "Right-click 'Ask TuxAgent' in GNOME Files",
        "category": "file-manager",
        "desktop": "GNOME",
        "dependencies": ["python3-nautilus"],
        "install_path": "~/.local/share/nautilus-python/extensions",
        "files": ["tuxagent-nautilus.py"],
        "post_install": "nautilus -q 2>/dev/null || true",
        "post_remove": "nautilus -q 2>/dev/null || true",
    },
    "nemo": {
        "name": "Nemo Integration",
        "description": "Right-click 'Ask TuxAgent' in Cinnamon Files",
        "category": "file-manager",
        "desktop": "Cinnamon",
        "dependencies": ["nemo-python"],
        "install_path": "~/.local/share/nemo-python/extensions",
        "files": ["tuxagent-nemo.py"],
        "post_install": "nemo -q 2>/dev/null || true",
        "post_remove": "nemo -q 2>/dev/null || true",
    },
    "dolphin": {
        "name": "Dolphin Integration",
        "description": "Right-click 'Ask TuxAgent' in KDE Dolphin",
        "category": "file-manager",
        "desktop": "KDE",
        "dependencies": [],
        "install_path": "~/.local/share/kservices5/ServiceMenus",
        "files": ["tuxagent-dolphin.desktop"],
        "post_install": "",
        "post_remove": "",
    },
    "thunar": {
        "name": "Thunar Integration",
        "description": "Right-click 'Ask TuxAgent' in XFCE Thunar",
        "category": "file-manager",
        "desktop": "XFCE",
        "dependencies": [],
        "install_path": "~/.config/Thunar/uca.xml",
        "files": [],  # Thunar uses XML config
        "custom_install": True,
        "post_install": "",
        "post_remove": "",
    },
}


@dataclass
class ExtensionStatus:
    """Status of an extension"""
    name: str
    installed: bool
    available: bool
    description: str
    category: str
    desktop: str


class ExtensionManager:
    """Manages TuxAgent extensions"""

    def __init__(self):
        self.config_dir = Path.home() / ".config" / "tuxagent"
        self.config_file = self.config_dir / "extensions.json"
        self.extensions_src = Path(__file__).parent.parent.parent / "extensions"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load installed extensions
        self._installed = self._load_installed()

    def _load_installed(self) -> Dict[str, Any]:
        """Load list of installed extensions"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"installed": []}

    def _save_installed(self):
        """Save list of installed extensions"""
        with open(self.config_file, 'w') as f:
            json.dump(self._installed, f, indent=2)

    def list_extensions(self) -> List[ExtensionStatus]:
        """List all available extensions with their status"""
        result = []
        for ext_id, ext_info in EXTENSIONS.items():
            status = ExtensionStatus(
                name=ext_id,
                installed=self.is_installed(ext_id),
                available=self._is_available(ext_id),
                description=ext_info["description"],
                category=ext_info["category"],
                desktop=ext_info["desktop"],
            )
            result.append(status)
        return result

    def _is_available(self, extension_id: str) -> bool:
        """Check if extension source files exist"""
        if extension_id not in EXTENSIONS:
            return False

        ext_info = EXTENSIONS[extension_id]
        ext_dir = self.extensions_src / extension_id

        # Check if extension directory exists
        if not ext_dir.exists():
            return False

        # Check if all required files exist
        for filename in ext_info.get("files", []):
            if not (ext_dir / filename).exists():
                return False

        return True

    def is_installed(self, extension_id: str) -> bool:
        """Check if an extension is installed"""
        return extension_id in self._installed.get("installed", [])

    def check_dependencies(self, extension_id: str) -> Dict[str, Any]:
        """
        Check if all dependencies for an extension are satisfied.

        Returns:
            Dict with 'satisfied' bool, 'missing' list, and 'install_commands' dict
        """
        if extension_id not in EXTENSIONS:
            return {"satisfied": False, "missing": [], "install_commands": {}}

        ext_info = EXTENSIONS[extension_id]
        missing = []
        install_commands = {}

        for dep in ext_info.get("dependencies", []):
            if not self._check_dependency(dep):
                missing.append(dep)
                # Generate install command for this dependency
                install_commands[dep] = self._get_install_command(dep)

        return {
            "satisfied": len(missing) == 0,
            "missing": missing,
            "install_commands": install_commands
        }

    def _get_install_command(self, dep: str) -> str:
        """Get the install command for a dependency based on the system's package manager"""
        if shutil.which("apt"):
            return f"sudo apt install {dep}"
        elif shutil.which("dnf"):
            return f"sudo dnf install {dep}"
        elif shutil.which("pacman"):
            # Arch uses different package names
            pkg_map = {
                "python3-nautilus": "python-nautilus",
                "nemo-python": "nemo-python",
            }
            pkg = pkg_map.get(dep, dep)
            return f"sudo pacman -S {pkg}"
        elif shutil.which("zypper"):
            return f"sudo zypper install {dep}"
        else:
            return f"Install package: {dep}"

    def install(self, extension_id: str, force: bool = False, auto_deps: bool = False) -> Dict[str, Any]:
        """
        Install an extension

        Args:
            extension_id: The extension to install
            force: Reinstall even if already installed
            auto_deps: Automatically install missing dependencies (requires sudo)

        Returns:
            Dict with 'success', 'message', and optionally 'warnings', 'missing_deps'
        """
        if extension_id not in EXTENSIONS:
            return {
                "success": False,
                "message": f"Unknown extension: {extension_id}"
            }

        if self.is_installed(extension_id) and not force:
            return {
                "success": False,
                "message": f"Extension '{extension_id}' is already installed. Use --force to reinstall."
            }

        ext_info = EXTENSIONS[extension_id]
        ext_dir = self.extensions_src / extension_id
        warnings = []

        # Check if source files exist
        if not self._is_available(extension_id):
            return {
                "success": False,
                "message": f"Extension files not found in {ext_dir}"
            }

        # Check dependencies FIRST - before doing anything else
        dep_check = self.check_dependencies(extension_id)
        if not dep_check["satisfied"]:
            missing = dep_check["missing"]
            commands = dep_check["install_commands"]

            if auto_deps:
                # Try to install dependencies automatically
                for dep in missing:
                    result = self._install_dependency(dep)
                    if not result["success"]:
                        return {
                            "success": False,
                            "message": f"Failed to install required dependency: {dep}",
                            "missing_deps": missing,
                            "install_commands": commands
                        }
            else:
                # Return with instructions for the user
                return {
                    "success": False,
                    "needs_deps": True,
                    "message": f"Missing required dependencies: {', '.join(missing)}",
                    "missing_deps": missing,
                    "install_commands": commands
                }

        # Create install directory
        install_path = Path(os.path.expanduser(ext_info["install_path"]))

        # Handle custom installers
        if ext_info.get("custom_install"):
            result = self._custom_install(extension_id)
            if not result["success"]:
                return result
        else:
            # Standard file copy installation
            install_path.mkdir(parents=True, exist_ok=True)

            for filename in ext_info.get("files", []):
                src_file = ext_dir / filename
                dst_file = install_path / filename

                try:
                    shutil.copy2(src_file, dst_file)
                    logger.info(f"Installed {filename} to {install_path}")
                except IOError as e:
                    return {
                        "success": False,
                        "message": f"Failed to copy {filename}: {e}"
                    }

        # Run post-install command
        post_install = ext_info.get("post_install", "")
        if post_install:
            try:
                subprocess.run(post_install, shell=True, check=False)
            except Exception as e:
                warnings.append(f"Post-install command failed: {e}")

        # Mark as installed
        if extension_id not in self._installed["installed"]:
            self._installed["installed"].append(extension_id)
            self._save_installed()

        result = {
            "success": True,
            "message": f"Extension '{ext_info['name']}' installed successfully!"
        }

        if warnings:
            result["warnings"] = warnings

        # Add helpful hints
        hints = self._get_install_hints(extension_id)
        if hints:
            result["hints"] = hints

        return result

    def remove(self, extension_id: str) -> Dict[str, Any]:
        """Remove an installed extension"""
        if extension_id not in EXTENSIONS:
            return {
                "success": False,
                "message": f"Unknown extension: {extension_id}"
            }

        if not self.is_installed(extension_id):
            return {
                "success": False,
                "message": f"Extension '{extension_id}' is not installed"
            }

        ext_info = EXTENSIONS[extension_id]
        install_path = Path(os.path.expanduser(ext_info["install_path"]))

        # Handle custom uninstallers
        if ext_info.get("custom_install"):
            result = self._custom_remove(extension_id)
            if not result["success"]:
                return result
        else:
            # Standard file removal
            for filename in ext_info.get("files", []):
                file_path = install_path / filename
                try:
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Removed {file_path}")
                except IOError as e:
                    return {
                        "success": False,
                        "message": f"Failed to remove {filename}: {e}"
                    }

        # Run post-remove command
        post_remove = ext_info.get("post_remove", "")
        if post_remove:
            try:
                subprocess.run(post_remove, shell=True, check=False)
            except Exception:
                pass

        # Mark as uninstalled
        if extension_id in self._installed["installed"]:
            self._installed["installed"].remove(extension_id)
            self._save_installed()

        return {
            "success": True,
            "message": f"Extension '{ext_info['name']}' removed successfully!"
        }

    def _check_dependency(self, dep: str) -> bool:
        """Check if a system dependency is installed"""
        # Try to import Python packages
        if dep.startswith("python3-"):
            pkg_name = dep.replace("python3-", "")
            try:
                __import__(pkg_name)
                return True
            except ImportError:
                pass

            # Special case for nautilus-python
            if "nautilus" in dep:
                try:
                    import gi
                    # Try both Nautilus 4.0 and 3.0
                    for version in ['4.0', '3.0']:
                        try:
                            gi.require_version('Nautilus', version)
                            from gi.repository import Nautilus
                            return True
                        except ValueError:
                            continue
                    return False
                except (ImportError, ValueError):
                    return False

        # Check for system packages via dpkg/rpm
        if shutil.which("dpkg"):
            result = subprocess.run(
                ["dpkg", "-l", dep],
                capture_output=True
            )
            return result.returncode == 0

        if shutil.which("rpm"):
            result = subprocess.run(
                ["rpm", "-q", dep],
                capture_output=True
            )
            return result.returncode == 0

        return False

    def _install_dependency(self, dep: str) -> Dict[str, Any]:
        """Attempt to install a system dependency"""
        pkg_managers = [
            (["apt", "install", "-y"], "apt"),
            (["dnf", "install", "-y"], "dnf"),
            (["pacman", "-S", "--noconfirm"], "pacman"),
        ]

        for cmd_base, pm_name in pkg_managers:
            if shutil.which(pm_name):
                try:
                    cmd = ["sudo"] + cmd_base + [dep]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return {"success": True, "message": f"Installed {dep}"}
                    else:
                        return {"success": False, "message": result.stderr}
                except Exception as e:
                    return {"success": False, "message": str(e)}

        return {"success": False, "message": "No supported package manager found"}

    def _get_install_hints(self, extension_id: str) -> List[str]:
        """Get helpful hints after installation"""
        hints = []

        if extension_id == "nautilus":
            hints.append("Restart Nautilus to activate: nautilus -q")
            hints.append("Then right-click any file to see 'Ask TuxAgent'")
        elif extension_id == "nemo":
            hints.append("Restart Nemo to activate: nemo -q")
        elif extension_id == "dolphin":
            hints.append("Right-click any file in Dolphin to see 'Ask TuxAgent'")

        return hints

    def _custom_install(self, extension_id: str) -> Dict[str, Any]:
        """Handle custom installation for extensions that need special handling"""
        if extension_id == "thunar":
            return self._install_thunar()
        return {"success": False, "message": "No custom installer defined"}

    def _custom_remove(self, extension_id: str) -> Dict[str, Any]:
        """Handle custom removal for extensions"""
        if extension_id == "thunar":
            return self._remove_thunar()
        return {"success": False, "message": "No custom remover defined"}

    def _install_thunar(self) -> Dict[str, Any]:
        """Install Thunar custom action"""
        uca_file = Path.home() / ".config" / "Thunar" / "uca.xml"
        uca_file.parent.mkdir(parents=True, exist_ok=True)

        # TuxAgent action entry
        action = '''
    <action>
        <icon>dialog-question-symbolic</icon>
        <name>Ask TuxAgent</name>
        <submenu></submenu>
        <unique-id>tuxagent-ask</unique-id>
        <command>tux ask "Tell me about this file: %f"</command>
        <description>Ask TuxAgent about this file</description>
        <range></range>
        <patterns>*</patterns>
        <startup-notify/>
        <directories/>
        <audio-files/>
        <image-files/>
        <other-files/>
        <text-files/>
        <video-files/>
    </action>
'''

        if uca_file.exists():
            content = uca_file.read_text()
            if "tuxagent-ask" in content:
                return {"success": True, "message": "Already installed"}

            # Insert before closing tag
            content = content.replace("</actions>", f"{action}</actions>")
            uca_file.write_text(content)
        else:
            # Create new file
            content = f'<?xml version="1.0" encoding="UTF-8"?>\n<actions>{action}</actions>'
            uca_file.write_text(content)

        return {"success": True, "message": "Thunar action installed"}

    def _remove_thunar(self) -> Dict[str, Any]:
        """Remove Thunar custom action"""
        uca_file = Path.home() / ".config" / "Thunar" / "uca.xml"

        if not uca_file.exists():
            return {"success": True, "message": "Nothing to remove"}

        content = uca_file.read_text()

        # Remove our action block
        import re
        pattern = r'\s*<action>.*?<unique-id>tuxagent-ask</unique-id>.*?</action>'
        content = re.sub(pattern, '', content, flags=re.DOTALL)

        uca_file.write_text(content)
        return {"success": True, "message": "Thunar action removed"}

    def detect_desktop(self) -> str:
        """Detect current desktop environment"""
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        session = os.environ.get("DESKTOP_SESSION", "").upper()

        if "GNOME" in desktop or "GNOME" in session:
            return "GNOME"
        elif "KDE" in desktop or "PLASMA" in desktop:
            return "KDE"
        elif "XFCE" in desktop:
            return "XFCE"
        elif "CINNAMON" in desktop:
            return "Cinnamon"
        elif "MATE" in desktop:
            return "MATE"
        else:
            return desktop or "Unknown"

    def get_recommended(self) -> List[str]:
        """Get recommended extensions for current desktop"""
        desktop = self.detect_desktop()
        recommended = []

        for ext_id, ext_info in EXTENSIONS.items():
            if ext_info["desktop"] == desktop:
                recommended.append(ext_id)

        return recommended
