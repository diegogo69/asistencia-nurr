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
            float dpiScale = 1.0f;
            using (Graphics g = this.CreateGraphics())
            {
                dpiScale = g.DpiX / 96.0f;
            }
            Func<int, int> S = (px) => (int)Math.Round(px * dpiScale);

            this.Text = "Asistencia-NURR - Servidor (Perfil Administrador)";
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(248, 250, 252);
            this.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular, GraphicsUnit.Point);

            // Contenedor principal vertical (Header + Content) sin superposiciones
            TableLayoutPanel mainLayout = new TableLayoutPanel();
            mainLayout.Location = new Point(0, 0);
            mainLayout.ColumnCount = 1;
            mainLayout.RowCount = 2;
            mainLayout.AutoSize = true;
            mainLayout.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            mainLayout.Margin = new Padding(0);
            mainLayout.Padding = new Padding(0);
            mainLayout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            mainLayout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            mainLayout.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            // 1. Banner Superior Institucional
            TableLayoutPanel headerPanel = new TableLayoutPanel();
            headerPanel.Dock = DockStyle.Fill;
            headerPanel.ColumnCount = 1;
            headerPanel.RowCount = 2;
            headerPanel.AutoSize = true;
            headerPanel.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            headerPanel.BackColor = Color.FromArgb(0, 86, 179);
            headerPanel.Padding = new Padding(S(24), S(16), S(24), S(16));
            headerPanel.Margin = new Padding(0);

            Label titleLabel = new Label();
            titleLabel.Text = "SISTEMA DE ASISTENCIA AUTOMATIZADA - ULA-NURR";
            titleLabel.Font = new Font("Segoe UI", 12F, FontStyle.Bold, GraphicsUnit.Point);
            titleLabel.ForeColor = Color.White;
            titleLabel.AutoSize = true;
            titleLabel.Margin = new Padding(0, 0, 0, S(4));

            Label subtitleLabel = new Label();
            subtitleLabel.Text = "Unidad de Soporte Técnico  |  Control de Administrador (Consola Oculta)";
            subtitleLabel.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular, GraphicsUnit.Point);
            subtitleLabel.ForeColor = Color.FromArgb(219, 234, 254);
            subtitleLabel.AutoSize = true;
            subtitleLabel.Margin = new Padding(0);

            headerPanel.Controls.Add(titleLabel, 0, 0);
            headerPanel.Controls.Add(subtitleLabel, 0, 1);
            mainLayout.Controls.Add(headerPanel, 0, 0);

            // 2. Contenedor Central de Contenido
            TableLayoutPanel contentPanel = new TableLayoutPanel();
            contentPanel.Dock = DockStyle.Fill;
            contentPanel.ColumnCount = 1;
            contentPanel.RowCount = 3;
            contentPanel.AutoSize = true;
            contentPanel.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            contentPanel.Padding = new Padding(S(24), S(20), S(24), S(22));
            contentPanel.Margin = new Padding(0);
            contentPanel.BackColor = Color.FromArgb(248, 250, 252);
            contentPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));

            // Tarjeta de Estado (borde sutil con panel contenedor)
            Panel statusBorder = new Panel();
            statusBorder.Dock = DockStyle.Top;
            statusBorder.AutoSize = true;
            statusBorder.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            statusBorder.MinimumSize = new Size(S(585), 0);
            statusBorder.BackColor = Color.FromArgb(203, 213, 225);
            statusBorder.Padding = new Padding(1);
            statusBorder.Margin = new Padding(0, 0, 0, S(14));

            TableLayoutPanel statusCard = new TableLayoutPanel();
            statusCard.Dock = DockStyle.Fill;
            statusCard.ColumnCount = 1;
            statusCard.RowCount = 3;
            statusCard.AutoSize = true;
            statusCard.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            statusCard.BackColor = Color.White;
            statusCard.Padding = new Padding(S(16), S(14), S(16), S(14));
            statusCard.Margin = new Padding(0);

            lblStatus = new Label();
            lblStatus.Text = "● Inicializando entorno y servidor en segundo plano...";
            lblStatus.Font = new Font("Segoe UI", 10.5F, FontStyle.Bold, GraphicsUnit.Point);
            lblStatus.ForeColor = Color.FromArgb(217, 119, 6);
            lblStatus.AutoSize = true;
            lblStatus.Margin = new Padding(0, 0, 0, S(8));

            lblUrl = new Label();
            lblUrl.Text = "Dirección Local: " + targetUrl;
            lblUrl.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular, GraphicsUnit.Point);
            lblUrl.ForeColor = Color.FromArgb(51, 65, 85);
            lblUrl.AutoSize = true;
            lblUrl.Margin = new Padding(0, 0, 0, S(6));

            lblLogs = new Label();
            lblLogs.Text = "Directorio de logs: " + logsDir;
            lblLogs.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular, GraphicsUnit.Point);
            lblLogs.ForeColor = Color.FromArgb(100, 116, 139);
            lblLogs.AutoSize = true;
            lblLogs.MaximumSize = new Size(S(575), 0);
            lblLogs.Margin = new Padding(0);

            statusCard.Controls.Add(lblStatus, 0, 0);
            statusCard.Controls.Add(lblUrl, 0, 1);
            statusCard.Controls.Add(lblLogs, 0, 2);
            statusBorder.Controls.Add(statusCard);
            contentPanel.Controls.Add(statusBorder, 0, 0);

            // Mensaje informativo
            Label infoLabel = new Label();
            infoLabel.Text = "La consola de comandos permanece oculta para mantener una operación limpia y segura.\r\nUtilice los botones inferiores o el perfil de administrador en la web para detener el servidor.";
            infoLabel.Font = new Font("Segoe UI", 9F, FontStyle.Regular, GraphicsUnit.Point);
            infoLabel.ForeColor = Color.FromArgb(71, 85, 105);
            infoLabel.AutoSize = true;
            infoLabel.MaximumSize = new Size(S(595), 0);
            infoLabel.Margin = new Padding(S(2), 0, S(2), S(18));
            contentPanel.Controls.Add(infoLabel, 0, 1);

            // Botonera Inferior alineada con espaciado automático
            TableLayoutPanel buttonBar = new TableLayoutPanel();
            buttonBar.Dock = DockStyle.Fill;
            buttonBar.ColumnCount = 4;
            buttonBar.RowCount = 1;
            buttonBar.AutoSize = true;
            buttonBar.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            buttonBar.Margin = new Padding(0);
            buttonBar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            buttonBar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            buttonBar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            buttonBar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));

            btnOpenBrowser = new Button();
            btnOpenBrowser.Text = "Abrir Navegador";
            btnOpenBrowser.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold, GraphicsUnit.Point);
            btnOpenBrowser.BackColor = Color.FromArgb(0, 86, 179);
            btnOpenBrowser.ForeColor = Color.White;
            btnOpenBrowser.FlatStyle = FlatStyle.Flat;
            btnOpenBrowser.FlatAppearance.BorderSize = 0;
            btnOpenBrowser.AutoSize = true;
            btnOpenBrowser.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            btnOpenBrowser.Padding = new Padding(S(14), S(7), S(14), S(7));
            btnOpenBrowser.MinimumSize = new Size(S(145), S(38));
            btnOpenBrowser.Margin = new Padding(0, 0, S(10), 0);
            btnOpenBrowser.Cursor = Cursors.Hand;
            btnOpenBrowser.Click += (s, e) => OpenBrowser();

            btnOpenLogs = new Button();
            btnOpenLogs.Text = "Carpeta de Logs";
            btnOpenLogs.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular, GraphicsUnit.Point);
            btnOpenLogs.BackColor = Color.FromArgb(226, 232, 240);
            btnOpenLogs.ForeColor = Color.FromArgb(30, 41, 59);
            btnOpenLogs.FlatStyle = FlatStyle.Flat;
            btnOpenLogs.FlatAppearance.BorderSize = 0;
            btnOpenLogs.AutoSize = true;
            btnOpenLogs.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            btnOpenLogs.Padding = new Padding(S(14), S(7), S(14), S(7));
            btnOpenLogs.MinimumSize = new Size(S(135), S(38));
            btnOpenLogs.Margin = new Padding(0, 0, S(10), 0);
            btnOpenLogs.Cursor = Cursors.Hand;
            btnOpenLogs.Click += (s, e) => OpenLogsFolder();

            Panel spacer = new Panel();
            spacer.Size = new Size(S(24), S(10));
            spacer.Margin = new Padding(0);

            btnStopServer = new Button();
            btnStopServer.Text = "Detener Servidor";
            btnStopServer.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold, GraphicsUnit.Point);
            btnStopServer.BackColor = Color.FromArgb(220, 38, 38);
            btnStopServer.ForeColor = Color.White;
            btnStopServer.FlatStyle = FlatStyle.Flat;
            btnStopServer.FlatAppearance.BorderSize = 0;
            btnStopServer.AutoSize = true;
            btnStopServer.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            btnStopServer.Padding = new Padding(S(14), S(7), S(14), S(7));
            btnStopServer.MinimumSize = new Size(S(145), S(38));
            btnStopServer.Margin = new Padding(0);
            btnStopServer.Cursor = Cursors.Hand;
            btnStopServer.Click += (s, e) => RequestShutdown();

            buttonBar.Controls.Add(btnOpenBrowser, 0, 0);
            buttonBar.Controls.Add(btnOpenLogs, 1, 0);
            buttonBar.Controls.Add(spacer, 2, 0);
            buttonBar.Controls.Add(btnStopServer, 3, 0);
            contentPanel.Controls.Add(buttonBar, 0, 2);

            mainLayout.Controls.Add(contentPanel, 0, 1);
            this.Controls.Add(mainLayout);
            this.ClientSize = mainLayout.GetPreferredSize(Size.Empty);
            mainLayout.Dock = DockStyle.Fill;

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

            string previewPath = Environment.GetEnvironmentVariable("ASISTENCIA_CAPTURE_PREVIEW");
            if (!string.IsNullOrEmpty(previewPath))
            {
                try
                {
                    this.PerformLayout();
                    this.Refresh();
                    using (Bitmap bmp = new Bitmap(this.Width, this.Height))
                    {
                        this.DrawToBitmap(bmp, new Rectangle(0, 0, this.Width, this.Height));
                        bmp.Save(previewPath, System.Drawing.Imaging.ImageFormat.Png);
                    }
                }
                catch { }
            }
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
