using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace AsistenciaNURR.Launcher
{
    public class Program
    {
        [STAThread]
        public static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(baseDir);

            Application.Run(new MainForm(baseDir));
        }
    }

    public class MainForm : Form
    {
        private readonly string baseDir;
        private readonly string logsDir;
        private readonly string launcherLogFile;
        private readonly string serverLogFile;
        private readonly string targetUrl = "https://localhost:8000";

        private Process serverProcess;
        private StreamWriter serverLogWriter;
        private System.Windows.Forms.Timer monitorTimer;
        private NotifyIcon trayIcon;

        private Label lblStatus;
        private Label lblUrl;
        private Label lblLogs;
        private Button btnOpenBrowser;
        private Button btnOpenLogs;
        private Button btnStopServer;

        public MainForm(string baseDir)
        {
            this.baseDir = baseDir;
            this.logsDir = Path.Combine(baseDir, "logs");
            this.launcherLogFile = Path.Combine(logsDir, "launcher.log");
            this.serverLogFile = Path.Combine(logsDir, "servidor.log");

            Directory.CreateDirectory(logsDir);
            Log("==================================================");
            Log("Iniciando AsistenciaNURR Launcher (Windows 10 GUI)");
            Log("Ruta Base: " + baseDir);
            Log("Ruta Logs: " + logsDir);
            Log("==================================================");

            InitializeComponents();
            InitializeTrayIcon();

            this.Load += (s, e) => StartServerWorkflow();
            this.FormClosing += MainForm_FormClosing;
        }

        private void Log(string message)
        {
            try
            {
                string line = string.Format("[{0:yyyy-MM-dd HH:mm:ss}] [LAUNCHER-WIN10] {1}", DateTime.Now, message);
                File.AppendAllText(launcherLogFile, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }

        private void InitializeComponents()
        {
            this.Text = "Asistencia-NURR - Servidor (Perfil Administrador)";
            this.ClientSize = new Size(530, 360);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(248, 250, 252);
            this.Font = new Font("Segoe UI", 9F, FontStyle.Regular, GraphicsUnit.Point);

            // Banner Superior Institucional
            Panel headerPanel = new Panel();
            headerPanel.Dock = DockStyle.Top;
            headerPanel.Height = 75;
            headerPanel.BackColor = Color.FromArgb(0, 86, 179);

            Label titleLabel = new Label();
            titleLabel.Text = "SISTEMA DE ASISTENCIA AUTOMATIZADA - ULA-NURR";
            titleLabel.Font = new Font("Segoe UI", 11.5F, FontStyle.Bold);
            titleLabel.ForeColor = Color.White;
            titleLabel.AutoSize = true;
            titleLabel.Location = new Point(20, 14);

            Label subtitleLabel = new Label();
            subtitleLabel.Text = "Unidad de Soporte Técnico | Control de Administrador (Consola Oculta)";
            subtitleLabel.Font = new Font("Segoe UI", 9F);
            subtitleLabel.ForeColor = Color.FromArgb(224, 231, 255);
            subtitleLabel.AutoSize = true;
            subtitleLabel.Location = new Point(20, 42);

            headerPanel.Controls.Add(titleLabel);
            headerPanel.Controls.Add(subtitleLabel);
            this.Controls.Add(headerPanel);

            // Contenedor Central
            Panel contentPanel = new Panel();
            contentPanel.Dock = DockStyle.Fill;
            contentPanel.Padding = new Padding(24, 18, 24, 18);
            contentPanel.BackColor = Color.FromArgb(248, 250, 252);

            // Tarjeta de Estado
            Panel statusCard = new Panel();
            statusCard.Location = new Point(24, 20);
            statusCard.Size = new Size(482, 105);
            statusCard.BackColor = Color.White;
            statusCard.BorderStyle = BorderStyle.FixedSingle;

            lblStatus = new Label();
            lblStatus.Text = "● Inicializando entorno y servidor en segundo plano...";
            lblStatus.Font = new Font("Segoe UI", 10.5F, FontStyle.Bold);
            lblStatus.ForeColor = Color.FromArgb(217, 119, 6);
            lblStatus.Location = new Point(14, 12);
            lblStatus.AutoSize = true;

            lblUrl = new Label();
            lblUrl.Text = "Dirección Local: " + targetUrl;
            lblUrl.Font = new Font("Segoe UI", 9.5F);
            lblUrl.ForeColor = Color.FromArgb(71, 85, 105);
            lblUrl.Location = new Point(14, 42);
            lblUrl.AutoSize = true;

            lblLogs = new Label();
            lblLogs.Text = "Directorio de logs: " + logsDir;
            lblLogs.Font = new Font("Segoe UI", 8.5F);
            lblLogs.ForeColor = Color.FromArgb(100, 116, 139);
            lblLogs.Location = new Point(14, 70);
            lblLogs.AutoSize = true;

            statusCard.Controls.Add(lblStatus);
            statusCard.Controls.Add(lblUrl);
            statusCard.Controls.Add(lblLogs);
            contentPanel.Controls.Add(statusCard);

            // Mensaje informativo
            Label infoLabel = new Label();
            infoLabel.Text = "La consola de comandos está oculta para mantener la operación limpia y protegida.\r\nUtilice esta interfaz o el perfil de administrador en la aplicación web para detener el servicio.";
            infoLabel.Font = new Font("Segoe UI", 8.5F);
            infoLabel.ForeColor = Color.FromArgb(100, 116, 139);
            infoLabel.Location = new Point(24, 140);
            infoLabel.Size = new Size(482, 35);
            contentPanel.Controls.Add(infoLabel);

            // Botonera Inferior
            btnOpenBrowser = new Button();
            btnOpenBrowser.Text = "🌐 Abrir Navegador";
            btnOpenBrowser.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            btnOpenBrowser.BackColor = Color.FromArgb(0, 86, 179);
            btnOpenBrowser.ForeColor = Color.White;
            btnOpenBrowser.FlatStyle = FlatStyle.Flat;
            btnOpenBrowser.FlatAppearance.BorderSize = 0;
            btnOpenBrowser.Size = new Size(140, 36);
            btnOpenBrowser.Location = new Point(24, 205);
            btnOpenBrowser.Cursor = Cursors.Hand;
            btnOpenBrowser.Click += (s, e) => OpenBrowser();
            contentPanel.Controls.Add(btnOpenBrowser);

            btnOpenLogs = new Button();
            btnOpenLogs.Text = "📂 Ver Logs";
            btnOpenLogs.Font = new Font("Segoe UI", 9F);
            btnOpenLogs.BackColor = Color.FromArgb(226, 232, 240);
            btnOpenLogs.ForeColor = Color.FromArgb(30, 41, 59);
            btnOpenLogs.FlatStyle = FlatStyle.Flat;
            btnOpenLogs.FlatAppearance.BorderSize = 0;
            btnOpenLogs.Size = new Size(110, 36);
            btnOpenLogs.Location = new Point(172, 205);
            btnOpenLogs.Cursor = Cursors.Hand;
            btnOpenLogs.Click += (s, e) => OpenLogsFolder();
            contentPanel.Controls.Add(btnOpenLogs);

            btnStopServer = new Button();
            btnStopServer.Text = "🛑 Detener Servidor";
            btnStopServer.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            btnStopServer.BackColor = Color.FromArgb(220, 38, 38);
            btnStopServer.ForeColor = Color.White;
            btnStopServer.FlatStyle = FlatStyle.Flat;
            btnStopServer.FlatAppearance.BorderSize = 0;
            btnStopServer.Size = new Size(145, 36);
            btnStopServer.Location = new Point(361, 205);
            btnStopServer.Cursor = Cursors.Hand;
            btnStopServer.Click += (s, e) => RequestShutdown();
            contentPanel.Controls.Add(btnStopServer);

            this.Controls.Add(contentPanel);

            // Timer de monitoreo continuo
            monitorTimer = new System.Windows.Forms.Timer();
            monitorTimer.Interval = 1500;
            monitorTimer.Tick += MonitorTimer_Tick;
        }

        private void InitializeTrayIcon()
        {
            try
            {
                trayIcon = new NotifyIcon();
                trayIcon.Text = "Asistencia-NURR Servidor";
                trayIcon.Icon = SystemIcons.Application;
                trayIcon.Visible = true;

                ContextMenuStrip menu = new ContextMenuStrip();
                menu.Items.Add("Abrir Navegador", null, (s, e) => OpenBrowser());
                menu.Items.Add("Ver Carpeta de Logs", null, (s, e) => OpenLogsFolder());
                menu.Items.Add("-");
                menu.Items.Add("Detener Servidor", null, (s, e) => RequestShutdown());

                trayIcon.ContextMenuStrip = menu;
                trayIcon.DoubleClick += (s, e) =>
                {
                    this.Show();
                    this.WindowState = FormWindowState.Normal;
                    this.BringToFront();
                };
            }
            catch { }
        }

        private string FindOrSetupPython()
        {
            string venvPy = Path.Combine(baseDir, "venv", "Scripts", "python.exe");
            if (File.Exists(venvPy)) return venvPy;

            string parentVenvPy = Path.Combine(baseDir, "..", "venv", "Scripts", "python.exe");
            if (File.Exists(parentVenvPy)) return Path.GetFullPath(parentVenvPy);

            // Si no existe venv pero existe requirements.txt, intentar crearlo con el python del sistema
            string sysPy = "python.exe";
            string reqFile = Path.Combine(baseDir, "requirements.txt");
            if (File.Exists(reqFile))
            {
                this.Invoke(new Action(() =>
                {
                    lblStatus.Text = "● Creando entorno virtual e instalando librerías...";
                }));
                Log("Creando entorno virtual 'venv'...");
                RunHiddenProcess(sysPy, "-m venv venv");

                if (File.Exists(venvPy))
                {
                    Log("Instalando dependencias desde requirements.txt...");
                    string venvPip = Path.Combine(baseDir, "venv", "Scripts", "pip.exe");
                    RunHiddenProcess(venvPip, "install -r requirements.txt");
                    return venvPy;
                }
            }

            return sysPy;
        }

        private void EnsurePrerequisites(string pythonExe)
        {
            string certFile = Path.Combine(baseDir, "certs", "cert.pem");
            string keyFile = Path.Combine(baseDir, "certs", "key.pem");
            if (!File.Exists(certFile) || !File.Exists(keyFile))
            {
                this.Invoke(new Action(() =>
                {
                    lblStatus.Text = "● Generando certificados SSL locales para LAN...";
                }));
                Log("Certificados SSL locales ausentes. Ejecutando generador...");
                RunHiddenProcess(pythonExe, "generate_certs.py");
            }

            string dbFile = Path.Combine(baseDir, "asistencia_nurr.db");
            if (!File.Exists(dbFile) || new FileInfo(dbFile).Length == 0)
            {
                this.Invoke(new Action(() =>
                {
                    lblStatus.Text = "● Inicializando base de datos y datos maestros...";
                }));
                Log("Base de datos no encontrada. Inicializando tablas y sembrado inicial...");
                RunHiddenProcess(pythonExe, "reset_db.py");
            }
        }

        private void RunHiddenProcess(string exe, string args)
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = exe;
                psi.Arguments = args;
                psi.WorkingDirectory = baseDir;
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                using (Process p = Process.Start(psi))
                {
                    p.WaitForExit(90000);
                }
            }
            catch (Exception ex)
            {
                Log("Error ejecutando proceso preparatorio: " + ex.Message);
            }
        }

        private bool CheckServerHealth()
        {
            try
            {
                ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072 | (SecurityProtocolType)768 | SecurityProtocolType.Tls;
                ServicePointManager.ServerCertificateValidationCallback =
                    (sender, certificate, chain, sslPolicyErrors) => true;

                HttpWebRequest req = (HttpWebRequest)WebRequest.Create("https://127.0.0.1:8000/api/health");
                req.Timeout = 1500;
                req.UserAgent = "AsistenciaNURR-WindowsLauncher";

                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                {
                    return resp.StatusCode == HttpStatusCode.OK;
                }
            }
            catch
            {
                return false;
            }
        }

        private void StartServerWorkflow()
        {
            Thread bgThread = new Thread(() =>
            {
                string py = FindOrSetupPython();
                Log("Python seleccionado: " + py);
                EnsurePrerequisites(py);

                if (CheckServerHealth())
                {
                    Log("El servidor ya se encontraba activo en el puerto 8000.");
                    this.Invoke(new Action(() =>
                    {
                        OnServerActive();
                        OpenBrowser();
                    }));
                    return;
                }

                // Iniciar proceso Uvicorn sin ventana de comandos
                try
                {
                    this.Invoke(new Action(() =>
                    {
                        lblStatus.Text = "● Iniciando servidor web HTTPS (Consola oculta)...";
                    }));

                    serverLogWriter = new StreamWriter(new FileStream(serverLogFile, FileMode.Append, FileAccess.Write, FileShare.ReadWrite), Encoding.UTF8);

                    ProcessStartInfo psi = new ProcessStartInfo();
                    psi.FileName = py;
                    psi.Arguments = "-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem";
                    psi.WorkingDirectory = baseDir;
                    psi.CreateNoWindow = true;
                    psi.UseShellExecute = false;
                    psi.WindowStyle = ProcessWindowStyle.Hidden;
                    psi.RedirectStandardOutput = true;
                    psi.RedirectStandardError = true;
                    psi.StandardOutputEncoding = Encoding.UTF8;
                    psi.StandardErrorEncoding = Encoding.UTF8;
                    psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

                    serverProcess = new Process();
                    serverProcess.StartInfo = psi;
                    serverProcess.OutputDataReceived += (s, e) =>
                    {
                        if (e.Data != null && serverLogWriter != null)
                        {
                            try { serverLogWriter.WriteLine(e.Data); serverLogWriter.Flush(); } catch { }
                        }
                    };
                    serverProcess.ErrorDataReceived += (s, e) =>
                    {
                        if (e.Data != null && serverLogWriter != null)
                        {
                            try { serverLogWriter.WriteLine("[STDERR] " + e.Data); serverLogWriter.Flush(); } catch { }
                        }
                    };

                    serverProcess.Start();
                    serverProcess.BeginOutputReadLine();
                    serverProcess.BeginErrorReadLine();
                    Log("Proceso Uvicorn iniciado exitosamente con PID: " + serverProcess.Id);

                    // Esperar health check
                    bool online = false;
                    for (int i = 0; i < 40; i++)
                    {
                        Thread.Sleep(500);
                        if (CheckServerHealth())
                        {
                            online = true;
                            break;
                        }
                        if (serverProcess.HasExited) break;
                    }

                    if (online)
                    {
                        Log("Servidor listo y verificado.");
                        this.Invoke(new Action(() =>
                        {
                            OnServerActive();
                            if (Environment.GetEnvironmentVariable("ASISTENCIA_SKIP_BROWSER") != "1")
                            {
                                OpenBrowser();
                            }
                        }));
                    }
                    else
                    {
                        Log("No se pudo confirmar el inicio del servidor.");
                        this.Invoke(new Action(() =>
                        {
                            lblStatus.Text = "● Error al iniciar el servidor";
                            lblStatus.ForeColor = Color.FromArgb(220, 38, 38);
                            MessageBox.Show(this, "El servidor no respondió a tiempo.\nConsulte el registro en: " + serverLogFile,
                                "Error de Servidor", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        }));
                    }
                }
                catch (Exception ex)
                {
                    Log("Error crítico al iniciar servidor: " + ex.Message);
                    this.Invoke(new Action(() =>
                    {
                        lblStatus.Text = "● Error: " + ex.Message;
                        lblStatus.ForeColor = Color.FromArgb(220, 38, 38);
                    }));
                }
            });

            bgThread.IsBackground = true;
            bgThread.Start();
        }

        private void OnServerActive()
        {
            lblStatus.Text = "● Servidor Activo (HTTPS En Línea)";
            lblStatus.ForeColor = Color.FromArgb(22, 163, 74);
            btnOpenBrowser.Enabled = true;
            monitorTimer.Start();
        }

        private void MonitorTimer_Tick(object sender, EventArgs e)
        {
            if (serverProcess != null && serverProcess.HasExited)
            {
                monitorTimer.Stop();
                Log("Servidor finalizado externamente (código de salida: " + serverProcess.ExitCode + ").");
                lblStatus.Text = "● Servidor detenido desde la interfaz web";
                lblStatus.ForeColor = Color.FromArgb(100, 116, 139);
                btnStopServer.Enabled = false;
                btnOpenBrowser.Enabled = false;

                try
                {
                    if (trayIcon != null)
                    {
                        trayIcon.ShowBalloonTip(
                            2000,
                            "Asistencia-NURR",
                            "El servidor ha sido detenido de forma ordenada.",
                            ToolTipIcon.Info
                        );
                    }
                }
                catch { }

                System.Windows.Forms.Timer closeTimer = new System.Windows.Forms.Timer();
                closeTimer.Interval = 1500;
                closeTimer.Tick += (cs, ce) =>
                {
                    closeTimer.Stop();
                    CloseAndCleanup();
                };
                closeTimer.Start();
            }
        }

        private void OpenBrowser()
        {
            try
            {
                Log("Abriendo navegador en: " + targetUrl);
                Process.Start(new ProcessStartInfo(targetUrl) { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                Log("Error al abrir navegador: " + ex.Message);
            }
        }

        private void OpenLogsFolder()
        {
            try
            {
                Process.Start("explorer.exe", logsDir);
            }
            catch (Exception ex)
            {
                Log("Error abriendo carpeta logs: " + ex.Message);
            }
        }

        private void RequestShutdown()
        {
            DialogResult res = MessageBox.Show(this,
                "¿Está seguro de que desea detener la ejecución del servidor Asistencia-NURR?\n\n" +
                "El servidor se apagará de forma segura y todos los registros se guardarán en la carpeta 'logs'.",
                "Detener Servidor",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning);

            if (res == DialogResult.Yes)
            {
                StopServerProcess();
                CloseAndCleanup();
            }
        }

        private void StopServerProcess()
        {
            Log("Detención del servidor solicitada por el administrador.");
            lblStatus.Text = "● Deteniendo servidor...";
            lblStatus.ForeColor = Color.FromArgb(217, 119, 6);
            this.Refresh();

            if (serverProcess != null && !serverProcess.HasExited)
            {
                try
                {
                    int pid = serverProcess.Id;
                    Log("Terminando árbol de procesos para PID: " + pid);
                    ProcessStartInfo psi = new ProcessStartInfo();
                    psi.FileName = "taskkill";
                    psi.Arguments = string.Format("/PID {0} /T /F", pid);
                    psi.CreateNoWindow = true;
                    psi.UseShellExecute = false;
                    using (Process killProc = Process.Start(psi))
                    {
                        killProc.WaitForExit(5000);
                    }
                }
                catch (Exception ex)
                {
                    Log("Excepción al detener proceso: " + ex.Message);
                }
            }
            Log("Servidor detenido exitosamente.");
        }

        private void MainForm_FormClosing(object sender, FormClosingEventArgs e)
        {
            if (serverProcess != null && !serverProcess.HasExited)
            {
                DialogResult res = MessageBox.Show(this,
                    "El servidor Asistencia-NURR continúa activo en segundo plano.\n\n" +
                    "¿Desea detener el servidor antes de salir?\n\n" +
                    "• Sí: Detiene el servidor y cierra la aplicación.\n" +
                    "• No: Cancelar y volver al panel.",
                    "Confirmación de Salida",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);

                if (res == DialogResult.Yes)
                {
                    StopServerProcess();
                    CloseAndCleanup();
                }
                else
                {
                    e.Cancel = true;
                }
            }
            else
            {
                CloseAndCleanup();
            }
        }

        private void CloseAndCleanup()
        {
            try
            {
                monitorTimer.Stop();
                if (trayIcon != null)
                {
                    trayIcon.Visible = false;
                    trayIcon.Dispose();
                }
                if (serverLogWriter != null)
                {
                    serverLogWriter.Flush();
                    serverLogWriter.Close();
                }
            }
            catch { }
            finally
            {
                Environment.Exit(0);
            }
        }
    }
}
