#!/usr/bin/env python3
import ast
import tokenize
import io
import os
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass

@dataclass
class CodeContext:
    """Represents the context of a code block including imports, variables, and scope."""
    imports: List[str]
    variables: Dict[str, str]  # variable_name: type_hint
    functions: List[str]
    classes: List[str]
    scope_level: int

@dataclass
class CodeSuggestion:
    """Represents a code completion or improvement suggestion."""
    suggestion: str
    confidence: float
    context: str
    category: str  # 'completion', 'refactor', 'improvement'

class CodeAnalyzer:
    """Advanced code analysis and suggestion engine."""
    
    def __init__(self):
        self.context_cache: Dict[str, CodeContext] = {}
        self.suggestion_threshold = 0.7
    
    def analyze_file(self, file_path: str) -> CodeContext:
        """Analyze a Python file and extract its context."""
        if file_path in self.context_cache:
            return self.context_cache[file_path]
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        context = self._extract_context(content)
        self.context_cache[file_path] = context
        return context
    
    def _extract_context(self, content: str) -> CodeContext:
        """Extract code context from source content."""
        tree = ast.parse(content)
        imports = []
        variables = {}
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(name.name for name in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module}.{node.names[0].name}")
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                variables[node.target.id] = ast.unparse(node.annotation)
                
        return CodeContext(
            imports=imports,
            variables=variables,
            functions=functions,
            classes=classes,
            scope_level=0
        )
    
    def get_suggestions(self, current_line: str, context: CodeContext) -> List[CodeSuggestion]:
        """Generate intelligent code suggestions based on current line and context."""
        suggestions = []
        
        # Analyze the current line for potential completions
        if current_line.strip().endswith('.'):
            # Object method completion
            obj_name = current_line.strip()[:-1]
            if obj_name in context.variables:
                var_type = context.variables[obj_name]
                suggestions.extend(self._get_method_suggestions(var_type))
        
        # Check for potential imports
        if 'import' in current_line or 'from' in current_line:
            suggestions.extend(self._get_import_suggestions(current_line, context))
        
        # Check for common patterns and suggest improvements
        suggestions.extend(self._analyze_for_improvements(current_line, context))
        
        return [s for s in suggestions if s.confidence >= self.suggestion_threshold]
    
    def _get_method_suggestions(self, type_hint: str) -> List[CodeSuggestion]:
        """Generate method suggestions for a given type."""
        # This would be expanded with a comprehensive type system
        common_methods = {
            'str': ['lower()', 'upper()', 'strip()', 'split()', 'replace()'],
            'list': ['append()', 'extend()', 'pop()', 'remove()', 'sort()'],
            'dict': ['keys()', 'values()', 'items()', 'get()', 'update()'],
        }
        
        suggestions = []
        if type_hint in common_methods:
            for method in common_methods[type_hint]:
                suggestions.append(CodeSuggestion(
                    suggestion=method,
                    confidence=0.9,
                    context=f"Common method for {type_hint}",
                    category='completion'
                ))
        
        return suggestions
    
    def _get_import_suggestions(self, current_line: str, context: CodeContext) -> List[CodeSuggestion]:
        """Suggest imports based on code context."""
        common_imports = {
            'os': 0.9,
            'sys': 0.85,
            'json': 0.8,
            'pathlib': 0.8,
            'typing': 0.85,
            'datetime': 0.8,
        }
        
        suggestions = []
        for module, confidence in common_imports.items():
            if module not in context.imports:
                suggestions.append(CodeSuggestion(
                    suggestion=f"import {module}",
                    confidence=confidence,
                    context="Common Python module",
                    category='completion'
                ))
                
        return suggestions
    
    def _analyze_for_improvements(self, current_line: str, context: CodeContext) -> List[CodeSuggestion]:
        """Analyze code for potential improvements and best practices."""
        suggestions = []
        
        # Check for potential list comprehension opportunities
        if 'for' in current_line and 'append' in current_line:
            suggestions.append(CodeSuggestion(
                suggestion="Consider using a list comprehension",
                confidence=0.8,
                context="Performance improvement",
                category='improvement'
            ))
        
        # Check for potential context manager usage
        if 'open(' in current_line and 'with' not in current_line:
            suggestions.append(CodeSuggestion(
                suggestion="Use 'with' statement for file operations",
                confidence=0.9,
                context="Best practice for resource management",
                category='improvement'
            ))
        
        return suggestions

    def analyze_complexity(self, content: str) -> Dict[str, Any]:
        """Analyze code complexity and provide metrics."""
        tree = ast.parse(content)
        metrics = {
            'cyclomatic_complexity': 0,
            'number_of_functions': 0,
            'number_of_classes': 0,
            'lines_of_code': len(content.splitlines()),
        }
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)):
                metrics['cyclomatic_complexity'] += 1
            elif isinstance(node, ast.FunctionDef):
                metrics['number_of_functions'] += 1
            elif isinstance(node, ast.ClassDef):
                metrics['number_of_classes'] += 1
        
        return metrics