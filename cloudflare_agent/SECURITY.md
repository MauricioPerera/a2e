# Seguridad - Cloudflare Agent

## ⚠️ Importante: Protección de Datos Sensibles

Este directorio contiene código que puede manejar credenciales y datos sensibles. Sigue estas prácticas de seguridad:

## ✅ Archivos Seguros para Commit

Los siguientes archivos están diseñados para ser seguros y pueden ser commiteados:

- `a2e_agent.ts` - Código fuente sin credenciales hardcodeadas
- `example_usage.ts` - Ejemplos con placeholders (`your-api-key-here`)
- `package.json` - Dependencias
- `tsconfig.json` - Configuración de TypeScript
- `wrangler.toml` - Variables comentadas con placeholders
- `README.md` - Documentación

## 🚫 Archivos que NUNCA deben ser Commiteados

Los siguientes archivos están en `.gitignore` y **NUNCA** deben ser agregados al repositorio:

- `.dev.vars` - Variables de entorno locales
- `.wrangler/` - Directorio de build de Wrangler
- `*.secrets.toml` - Archivos de secretos
- `wrangler.secrets.toml` - Secretos de Wrangler
- `*.local.toml` - Configuraciones locales
- `node_modules/` - Dependencias de Node.js

## 🔐 Configuración Segura

### Variables de Entorno

**NUNCA** pongas valores reales en `wrangler.toml`. En su lugar:

1. **Para desarrollo local**: Usa `.dev.vars` (está en `.gitignore`)
   ```toml
   # .dev.vars (NO commitear)
   A2E_SERVER_URL = "http://localhost:8000"
   A2E_API_KEY = "tu-api-key-real-aqui"
   ```

2. **Para producción**: Usa Cloudflare Secrets
   ```bash
   wrangler secret put A2E_API_KEY
   wrangler secret put A2E_SERVER_URL
   ```

### Ejemplo de `.dev.vars` (NO commitear)

```bash
# Este archivo está en .gitignore
A2E_SERVER_URL = "http://localhost:8000"
A2E_API_KEY = "tu-api-key-real"
A2E_TOKEN = "tu-token-real"
```

## ✅ Verificación Pre-Commit

Antes de hacer commit, verifica:

1. **No hay credenciales hardcodeadas**:
   ```bash
   grep -r "api.*key.*=.*['\"][^'\"]\{10,\}" . --exclude-dir=node_modules
   ```

2. **No hay archivos sensibles en staging**:
   ```bash
   git status
   # Verifica que .dev.vars, *.secrets.toml no estén listados
   ```

3. **Solo placeholders en ejemplos**:
   ```bash
   grep -r "your-api-key-here\|localhost\|example\.com" cloudflare_agent/
   ```

## 🔍 Checklist de Seguridad

Antes de hacer push:

- [ ] No hay valores reales de API keys en el código
- [ ] No hay tokens o passwords hardcodeados
- [ ] `.dev.vars` no está en el staging area
- [ ] `wrangler.toml` solo tiene variables comentadas
- [ ] Los ejemplos usan placeholders (`your-api-key-here`)
- [ ] No hay URLs de producción con credenciales
- [ ] `.gitignore` incluye todos los archivos sensibles

## 🛡️ Mejores Prácticas

1. **Usa variables de entorno**: Nunca hardcodees credenciales
2. **Usa Cloudflare Secrets**: Para producción, usa `wrangler secret`
3. **Revisa antes de commit**: Usa `git status` y `git diff`
4. **Usa placeholders**: En ejemplos y documentación
5. **Rotación de credenciales**: Si accidentalmente expusiste una, rótala inmediatamente

## 🚨 Si Expusiste una Credencial

Si accidentalmente pusheaste una credencial:

1. **Rota la credencial inmediatamente** en el servicio correspondiente
2. **Elimina del historial de Git** (si es necesario):
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch archivo-con-credencial" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. **Fuerza push** (solo si es absolutamente necesario y coordinado con el equipo)
4. **Notifica al equipo** sobre la exposición

## 📚 Referencias

- [Cloudflare Workers Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)
- [Git Security Best Practices](https://git-scm.com/docs/git-config#_syntax)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

