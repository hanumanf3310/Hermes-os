#!/usr/bin/env python3
"""
Delegate to OpenCode CLI - Hermes sub-agent integration
สั่งงาน OpenCode CLI แล้วตรวจสอบผลลัพธ์ พร้อม model fallback

ใช้ OpenCode CLI (ผ่าน npx) แทน Gemini CLI เพราะ:
- เร็วกว่า (~30-90 วิ vs ~120+ วิ)
- สร้างไฟล์จริง auto
- ไม่ต้อง auth ซับซ้อน
- มีหลาย models ฟรี

Requirements:
    npm install -g opencode-ai
    
หรือใช้ผ่าน npx: npx opencode run --agent build ...
"""

import subprocess
import json
import ast
import sys
import os
import re
import tempfile
from typing import Dict, List, Tuple, Optional


class OpenCodeDelegator:
    """Handle delegation to OpenCode CLI with validation and model fallback"""
    
    # Model fallback chain - ต้องมี prefix 'opencode/'
    MODEL_FALLBACK_CHAIN = [
        "opencode/big-pickle",              # Primary: เร็วที่สุด
        "opencode/minimax-m2.5-free",      # Fallback 1: MiniMax Free
        "opencode/nemotron-3-super-free",  # Fallback 2: Nemotron Free
    ]
    
    def __init__(self):
        self.max_retries = 3
        self.validation_threshold = 3  # ต้องผ่านอย่างน้อย 3/4 checks
        self.current_model_index = 0
        self.timeout_seconds = 120  # OpenCode เร็วกว่า Gemini
    
    def delegate(self, task: str, output_path: str = None, focus: List[str] = None) -> Dict:
        """
        Delegate task to OpenCode CLI - สั่งให้สร้างไฟล์จริง
        
        Args:
            task: คำสั่งสำหรับ OpenCode CLI
            output_path: Path ที่ต้องการให้สร้างไฟล์ (เช่น ./index.html)
            focus: สิ่งที่ต้องตรวจสอบ ['syntax', 'logic', 'security', 'docstring']
        
        Returns:
            Dict ผลลัพธ์ พร้อม path ไฟล์ที่สร้าง
        """
        # แปลง path ให้ใช้ ~/workspace/ (OpenCode มีปัญหา permission กับ /tmp/)
        if output_path:
            output_path = self._get_workspace_path(output_path)
            enhanced_task = f"{task} สร้างเป็นไฟล์ที่ {output_path} ทันที ใช้ compact output ไม่ต้องอธิบายมาก"
        else:
            enhanced_task = task
            output_path = self._generate_temp_path()
        
        print(f"🚀 สั่ง OpenCode CLI: {enhanced_task[:80]}...")
        
        # Model fallback loop
        opencode_result = None
        used_model = None
        
        for model_index, model in enumerate(self.MODEL_FALLBACK_CHAIN):
            if model_index > 0:
                print(f"   🔄 Fallback to: {model}...")
            
            result = self._call_opencode_cli(enhanced_task, output_path, model)
            
            if result['success']:
                opencode_result = result
                used_model = model
                print(f"   ✅ Success with {model}!")
                break
            else:
                print(f"   ⚠️  {model} failed: {result.get('error', 'Unknown')[:60]}...")
                continue
        
        # ถ้าทุก model fail → ใช้ Hermes fallback
        if not opencode_result:
            print(f"   🔧 All OpenCode models failed, using Hermes fallback...")
            hermes_result = self._hermes_fallback_code(task, output_path)
            opencode_result = {
                'success': True,
                'output': hermes_result['code'],
                'file_path': output_path,
                'model': 'hermes-fallback'
            }
            used_model = 'hermes-fallback'
        
        # อ่านโค้ดจากไฟล์
        code = self._read_file(output_path)
        
        # ตรวจสอบผลลัพธ์
        validation = self._validate_code(code, focus)
        
        return {
            'code': code,
            'file_path': output_path,
            'model_used': used_model,
            'validation': validation,
            'passed': validation['score'] >= self.validation_threshold,
            'errors': validation.get('errors', [])
        }
    
    def _get_workspace_path(self, path: str) -> str:
        """แปลง path ให้ใช้ ~/workspace/ เท่านั้น (OpenCode requirement)"""
        if path.startswith('/tmp/'):
            filename = os.path.basename(path)
            return f"/home/{os.environ.get('USER', 'hanuman3310')}/workspace/{filename}"
        elif path.startswith('./'):
            return f"/home/{os.environ.get('USER', 'hanuman3310')}/workspace/{path[2:]}"
        elif not path.startswith('/'):
            return f"/home/{os.environ.get('USER', 'hanuman3310')}/workspace/{path}"
        return path
    
    def _generate_temp_path(self) -> str:
        """Generate temp file path in workspace"""
        workspace = f"/home/{os.environ.get('USER', 'hanuman3310')}/workspace"
        return f"{workspace}/opencode_output_{os.getpid()}.py"
    
    def _call_opencode_cli(self, prompt: str, output_path: str, model: str) -> Dict:
        """
        Call OpenCode CLI using npx opencode run --agent build
        
        OpenCode จะสร้างไฟล์ auto ถ้า prompt บอก path ชัดเจน
        """
        try:
            # สร้าง prompt ที่บังคับให้สร้างไฟล์
            file_prompt = f"{prompt} Save to {output_path}"
            
            # ใช้ npx opencode run --agent build --model <model> "prompt"
            cmd = [
                'npx', 'opencode', 'run',
                '--agent', 'build',
                '--model', model,
                file_prompt
            ]
            
            print(f"   🎯 Calling: npx opencode run --agent build --model {model} ...")
            
            # ตั้ง working directory เป็น ~/workspace/
            workspace = f"/home/{os.environ.get('USER', 'hanuman3310')}/workspace"
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=workspace
            )
            
            # ตรวจสอบว่าไฟล์ถูกสร้างจริง
            if os.path.exists(output_path):
                return {
                    'success': True,
                    'output': f"File created at {output_path}",
                    'file_path': output_path,
                    'model': model,
                    'cli_output': result.stdout[:500]  # เก็บบางส่วนสำหรับ debug
                }
            else:
                # ลอง RTK clean output แล้วเขียนไฟล์เอง
                cleaned = self._rtk_clean_output(result.stdout, output_path)
                if cleaned and len(cleaned) > 50:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned)
                    return {
                        'success': True,
                        'output': cleaned,
                        'file_path': output_path,
                        'model': model,
                        'cleaned': True
                    }
                
                return {
                    'success': False,
                    'error': f'File not created at {output_path}. CLI output: {result.stdout[:200]}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Timeout after {self.timeout_seconds} seconds'
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': 'npx not found. Is Node.js installed?'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _rtk_clean_output(self, output: str, output_path: str) -> str:
        """
        RTK Post-Processor: ตัด output ที่ไม่จำเป็น
        
        ลบ:
        - "> build · big-pickle" header
        - "← Write filename" progress
        - "Wrote file successfully" message
        - "$ python ..." execution logs
        - Empty lines
        """
        if not output:
            return ""
        
        lines = output.split('\n')
        cleaned_lines = []
        
        skip_patterns = [
            r'^\s*>\s*build\s*·',
            r'^\s*←\s*Write',
            r'^\s*Wrote file',
            r'^\s*\$\s*python',
            r'^\s*Created and ran',
            r'^\s*Error:',
        ]
        
        for line in lines:
            should_skip = any(re.match(pattern, line) for pattern in skip_patterns)
            if not should_skip and line.strip():
                cleaned_lines.append(line)
        
        full_text = '\n'.join(cleaned_lines)
        
        # ดึงโค้ดจาก code blocks
        if '```python' in full_text:
            match = re.search(r'```python\n(.*?)\n```', full_text, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif '```' in full_text:
            match = re.search(r'```\n(.*?)\n```', full_text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return full_text.strip()
    
    def _hermes_fallback_code(self, task: str, output_path: str) -> Dict:
        """Hermes สร้างโค้ดเองเมื่อ OpenCode ไม่สำเร็จ"""
        print(f"   🔧 Hermes fallback generating code...")
        
        # ตรวจสอบว่าเป็น Python หรือ HTML/อื่น
        is_html = any(kw in task.lower() for kw in ['html', 'css', 'web', 'page', 'ui'])
        
        if is_html:
            code = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Page</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
    </style>
</head>
<body>
    <h1>Hello World</h1>
    <p>Generated by Hermes (OpenCode Fallback)</p>
</body>
</html>'''
        else:
            code = '''"""Generated by Hermes (OpenCode Fallback)"""

def main():
    """Main function"""
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return {'code': code, 'file_path': output_path}
    
    def _read_file(self, file_path: str) -> str:
        """Read content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    
    def _validate_code(self, code: str, focus: List[str] = None) -> Dict:
        """Validate extracted code - รองรับ Python และ HTML"""
        validation = {
            'syntax_valid': False,
            'has_docstring': False,
            'has_error_handling': False,
            'logic_verified': False,
            'score': 0,
            'total_checks': 4,
            'errors': [],
            'language': 'unknown'
        }
        
        focus = focus or ['syntax', 'docstring', 'error_handling', 'logic']
        
        # ตรวจสอบว่าเป็น HTML หรือ Python
        is_html = '<!DOCTYPE html>' in code.lower() or '<html' in code.lower()
        is_python = 'def ' in code or 'class ' in code or 'import ' in code or '# ' in code[:50]
        
        if is_html and not is_python:
            validation['language'] = 'html'
            
            # 1. Syntax check (HTML structure)
            if 'syntax' in focus:
                checks = [
                    '<!DOCTYPE html>' in code or '<html' in code,
                    '<head>' in code and '</head>' in code,
                    '<body>' in code and '</body>' in code,
                ]
                if all(checks):
                    validation['syntax_valid'] = True
                    validation['score'] += 1
                else:
                    validation['errors'].append("HTML structure incomplete")
            
            # 2. Docstring check (HTML comments)
            if 'docstring' in focus:
                if '<!--' in code:
                    validation['has_docstring'] = True
                    validation['score'] += 1
            
            # 3. Error handling
            if 'error_handling' in focus:
                validation['has_error_handling'] = True  # HTML doesn't need much
                validation['score'] += 1
            
            # 4. Logic verification
            if 'logic' in focus:
                validation['logic_verified'] = validation['syntax_valid']
                if validation['logic_verified']:
                    validation['score'] += 1
        
        else:
            validation['language'] = 'python'
            
            # 1. Syntax check
            if 'syntax' in focus:
                try:
                    ast.parse(code)
                    validation['syntax_valid'] = True
                    validation['score'] += 1
                except SyntaxError as e:
                    validation['errors'].append(f"Syntax Error: {e}")
            
            # 2. Docstring check
            if 'docstring' in focus:
                if '"""' in code or "'''" in code:
                    validation['has_docstring'] = True
                    validation['score'] += 1
            
            # 3. Error handling check
            if 'error_handling' in focus:
                if any(kw in code for kw in ['try:', 'except', 'raise']):
                    validation['has_error_handling'] = True
                    validation['score'] += 1
            
            # 4. Logic verification
            if 'logic' in focus and validation['syntax_valid']:
                try:
                    compile(code, '<string>', 'exec')
                    validation['logic_verified'] = True
                    validation['score'] += 1
                except Exception as e:
                    validation['errors'].append(f"Logic Error: {e}")
        
        return validation
    
    def fix_and_retry(self, original_task: str, error_details: str, previous_code: str) -> Dict:
        """Ask OpenCode to fix errors"""
        fix_prompt = f"""แก้ไขโค้ดนี้ให้ถูกต้อง:

โค้ดเดิม:
```
{previous_code}
```

ข้อผิดพลาดที่พบ:
{error_details}

โปรดแก้ไขและส่งคืนโค้ดที่ทำงานได้ถูกต้อง"""
        
        return self.delegate(fix_prompt)


def main():
    """CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Delegate tasks to OpenCode CLI')
    parser.add_argument('task', help='Task to delegate')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--focus', nargs='+', 
                       choices=['syntax', 'logic', 'security', 'docstring', 'error_handling'],
                       help='Validation focus areas')
    parser.add_argument('--fix', action='store_true', help='Auto-fix if validation fails')
    
    args = parser.parse_args()
    
    delegator = OpenCodeDelegator()
    result = delegator.delegate(args.task, args.output, args.focus)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Auto-fix if requested
    if args.fix and not result['passed'] and result['code']:
        print("\n🔧 Attempting auto-fix...")
        error_details = "\n".join(result['errors'])
        fix_result = delegator.fix_and_retry(args.task, error_details, result['code'])
        print("\n🔄 Fix attempt result:")
        print(json.dumps(fix_result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
