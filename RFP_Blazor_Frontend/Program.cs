using Microsoft.AspNetCore.Http.Features;
using MudBlazor.Services;
using RFP_Blazor_Frontend.Components;
using RFP_Blazor_Frontend.Helper;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

builder.Services.AddMudServices();

// Register the HttpClient as a singleton
builder.Services.AddSingleton(sp => new HttpClient
{
    BaseAddress = new Uri("http://127.0.0.1:5000/")
});

// Register the RfpClient as a singleton
builder.Services.AddSingleton<RfpClient>();

// Increase maximum request size for file uploads
builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 10485760; // 10 MB
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();

app.UseStaticFiles();
app.UseAntiforgery();

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
