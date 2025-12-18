# GitHub Pages - Troubleshooting

## Problema: Deployment Falla

Si el deployment de GitHub Pages está fallando, sigue estos pasos:

## ✅ Verificaciones

### 1. Verificar que GitHub Pages esté activado

1. Ve a: https://github.com/MauricioPerera/a2e/settings/pages
2. Verifica que **Source** esté configurado como: **GitHub Actions**
3. Si no está configurado, selecciónalo y guarda

### 2. Verificar el workflow

El workflow debe estar en: `.github/workflows/pages.yml`

Verifica que existe:
```bash
ls -la .github/workflows/pages.yml
```

### 3. Verificar archivos necesarios

```bash
# Debe existir docs/index.html
ls -la docs/index.html

# Debe existir .nojekyll
ls -la .nojekyll

# Debe haber archivos .md
ls -la *.md | head -5
```

## 🔍 Revisar Logs

1. Ve a: https://github.com/MauricioPerera/a2e/actions
2. Busca el workflow "Deploy GitHub Pages"
3. Haz clic en el run que falló
4. Revisa los logs del step "Build site" o "Copy documentation"

## 🛠️ Soluciones Comunes

### Error: "No files to deploy"

**Causa**: El directorio `_site` está vacío

**Solución**: Verifica que los archivos se estén copiando correctamente en el workflow

### Error: "Permission denied"

**Causa**: Permisos insuficientes

**Solución**: El workflow ya tiene los permisos correctos:
```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

### Error: "Environment not found"

**Causa**: El environment `github-pages` no está configurado

**Solución**: 
1. Ve a Settings → Environments
2. Crea el environment `github-pages` si no existe
3. O elimina la sección `environment` del workflow (se creará automáticamente)

### Error: "Workflow file not found"

**Causa**: El archivo del workflow no está en la rama correcta

**Solución**: Verifica que `.github/workflows/pages.yml` esté en la rama `main`

## 🔄 Workflow Simplificado

Si el workflow actual sigue fallando, puedes usar esta versión simplificada:

```yaml
name: Deploy GitHub Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v4
      - run: |
          mkdir -p _site
          cp docs/index.html _site/ 2>/dev/null || true
          cp *.md _site/ 2>/dev/null || true
          cp .nojekyll _site/ 2>/dev/null || true
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
      - uses: actions/deploy-pages@v4
```

## 📝 Checklist de Debugging

- [ ] GitHub Pages activado en Settings
- [ ] Source configurado como "GitHub Actions"
- [ ] Workflow existe en `.github/workflows/pages.yml`
- [ ] Workflow está en la rama `main`
- [ ] `docs/index.html` existe
- [ ] `.nojekyll` existe
- [ ] Hay archivos `.md` en el root
- [ ] Revisar logs del workflow en Actions

## 🆘 Si Nada Funciona

1. **Usar Static HTML workflow sugerido**:
   - En GitHub Pages settings, haz clic en "Configure" en la tarjeta "Static HTML"
   - Esto creará un workflow básico automáticamente

2. **Verificar manualmente**:
   ```bash
   # En local, verifica que estos archivos existen
   ls docs/index.html
   ls .nojekyll
   ls *.md
   ```

3. **Crear workflow mínimo**:
   - Elimina el workflow actual
   - Usa el workflow "Static HTML" sugerido por GitHub
   - Luego personalízalo según necesites

## ✅ Estado Actual

- ✅ Workflow simplificado y subido
- ✅ `.nojekyll` agregado
- ✅ `docs/index.html` existe
- ⏳ Esperando ejecución del workflow

---

**Si el problema persiste**, comparte los logs del workflow fallido y te ayudo a solucionarlo.

