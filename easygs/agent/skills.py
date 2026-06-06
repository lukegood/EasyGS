"""Skills loader for agent capabilities."""

import json
import os
import re
import shutil
from pathlib import Path

# Default builtin skills directory (relative to this file)
BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"
LEGACY_SKILL_METADATA_KEY = "nano" "bot"


class SkillsLoader:  # skills技能加载器
    """
    Loader for agent skills.
    
    Skills are markdown files (SKILL.md) that teach the agent how to use
    specific tools or perform certain tasks.
    """
    
    def __init__(self, workspace: Path, builtin_skills_dir: Path | None = None):
        self.workspace = workspace  # 工作空间
        self.workspace_skills = workspace / "skills"  # 工作空间的skills
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR  # 内置skills

    def list_skills(self, filter_unavailable: bool = True) -> list[dict[str, str]]:
        """
        List all available skills.
        
        Args:
            filter_unavailable: If True, filter out skills with unmet requirements.
        
        Returns:
            List of skill info dicts with 'name', 'path', 'source'.
        """
        skills = []
        
        # Workspace skills (highest priority)
        if self.workspace_skills.exists():  # 读取工作空间中的技能，高优先级
            for skill_dir in self.workspace_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        skills.append({"name": skill_dir.name, "path": str(skill_file), "source": "workspace"})
        
        # Built-in skills  # 读取内置的技能
        if self.builtin_skills and self.builtin_skills.exists():
            for skill_dir in self.builtin_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists() and not any(s["name"] == skill_dir.name for s in skills):  # 去重
                        skills.append({"name": skill_dir.name, "path": str(skill_file), "source": "builtin"})
        
        # Filter by requirements
        if filter_unavailable:  # 检查是否skills需求的环境或者bin满足，不满足就过滤
            return [s for s in skills if self._check_requirements(self._get_skill_meta(s["name"]))]
        return skills
    
    def load_skill(self, name: str) -> str | None:  # 加载skill
        """
        Load a skill by name.
        
        Args:
            name: Skill name (directory name).
        
        Returns:
            Skill content or None if not found.
        """
        # Check workspace first  加载工作空间skills
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            return workspace_skill.read_text(encoding="utf-8")
        
        # Check built-in  加载内置skills
        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                return builtin_skill.read_text(encoding="utf-8")
        
        return None
    
    def load_skills_for_context(self, skill_names: list[str]) -> str:  # 加载指定技能，格式化给LLM的上下文
        """
        Load specific skills for inclusion in agent context.
        
        Args:
            skill_names: List of skill names to load.
        
        Returns:
            Formatted skills content.
        """
        parts = []  # 存储每个skill的格式化内容
        for name in skill_names:  # 加载skills
            content = self.load_skill(name)
            if content:
                content = self._strip_frontmatter(content)  # 去除YAML frontmatter
                parts.append(f"### Skill: {name}\n\n{content}")  # 格式化
        
        return "\n\n---\n\n".join(parts) if parts else ""  # 分隔符连接所有技能，没有就返回空串
    
    def build_skills_summary(self) -> str:  # 构建skills摘要
        """
        Build a summary of all skills (name, description, path, availability).
        
        This is used for progressive loading - the agent can read the full
        skill content using read_file when needed.
        
        Returns:
            XML-formatted skills summary.
        """
        all_skills = self.list_skills(filter_unavailable=False)  # 获取所有skills
        if not all_skills:
            return ""
        
        def escape_xml(s: str) -> str:  # XML转义
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        lines = ["<skills>"]
        for s in all_skills:
            name = escape_xml(s["name"])  # name中xml转义
            path = s["path"]  # skills路径
            desc = escape_xml(self._get_skill_description(s["name"]))  # 读取skill描述并且xml转义
            skill_meta = self._get_skill_meta(s["name"])  # 读入meta信息
            available = self._check_requirements(skill_meta)  # 检查依赖是否满足
            
            lines.append(f"  <skill available=\"{str(available).lower()}\">")
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{desc}</description>")
            lines.append(f"    <location>{path}</location>")
            
            # Show missing requirements for unavailable skills
            if not available:
                missing = self._get_missing_requirements(skill_meta)
                if missing:
                    lines.append(f"    <requires>{escape_xml(missing)}</requires>")
            
            lines.append("  </skill>")
        lines.append("</skills>")
        
        return "\n".join(lines)  # 连成字符串
    
    def _get_missing_requirements(self, skill_meta: dict) -> str:  # 获取缺失的依赖
        """Get a description of missing requirements."""
        missing = []
        requires = skill_meta.get("requires", {})
        for b in requires.get("bins", []):
            if not shutil.which(b):
                missing.append(f"CLI: {b}")
        for env in requires.get("env", []):
            if not os.environ.get(env):
                missing.append(f"ENV: {env}")
        return ", ".join(missing)
    
    def _get_skill_description(self, name: str) -> str:  # 获取非meta嵌套的描述信息
        """Get the description of a skill from its frontmatter."""
        meta = self.get_skill_metadata(name)  # 读取meta信息
        if meta and meta.get("description"):
            return meta["description"]  # 如果有描述就返回描述，没有描述就返回skill的名称
        return name  # Fallback to skill name
    
    def _strip_frontmatter(self, content: str) -> str:  # 去除yaml中的格式
        """Remove YAML frontmatter from markdown content."""
        if content.startswith("---"):
            match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
            if match:
                return content[match.end():].strip()
        return content
    
    def _parse_easygs_metadata(self, raw: str) -> dict:  # 加载复杂嵌套信息
        """Parse EasyGS metadata JSON from frontmatter."""
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {}
            return data.get("easygs") or data.get(LEGACY_SKILL_METADATA_KEY, {})
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _check_requirements(self, skill_meta: dict) -> bool:  # 检查是否skills的技能被满足
        """Check if skill requirements are met (bins, env vars)."""
        requires = skill_meta.get("requires", {})
        for b in requires.get("bins", []):  # 检查bin
            if not shutil.which(b):
                return False
        for env in requires.get("env", []):  # 检查环境
            if not os.environ.get(env):
                return False
        return True
    
    def _get_skill_meta(self, name: str) -> dict:
        """Get EasyGS metadata for a skill (cached in frontmatter)."""
        meta = self.get_skill_metadata(name) or {}
        return self._parse_easygs_metadata(meta.get("metadata", ""))  # 读取嵌套复杂的meta信息
    
    def get_always_skills(self) -> list[str]:  # 获取标记为 always=true 的技能
        """Get skills marked as always=true that meet requirements."""
        result = []
        for s in self.list_skills(filter_unavailable=True):
            meta = self.get_skill_metadata(s["name"]) or {}
            skill_meta = self._parse_easygs_metadata(meta.get("metadata", ""))
            if skill_meta.get("always") or meta.get("always"):
                result.append(s["name"])
        return result
    
    def get_skill_metadata(self, name: str) -> dict | None:  # 获取skills的meta信息
        """
        Get metadata from a skill's frontmatter.
        
        Args:
            name: Skill name.
        
        Returns:
            Metadata dict or None.
        """
        content = self.load_skill(name)  # 读取skills
        if not content:
            return None
        
        if content.startswith("---"):  # 检查内容是否以---开头
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:  # 用正则表达式匹配，并且分割成字典
                # Simple YAML parsing
                metadata = {}
                for line in match.group(1).split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip('"\'')
                return metadata  # 返回meta信息
        
        return None
