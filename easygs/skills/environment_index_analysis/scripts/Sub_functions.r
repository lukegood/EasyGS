Forecast_next_year <- function(maxR1, maxR2, env_mean_trait, PTT_PTR, PTT_PTR_ind, exp_trait, trn_env, obs_prd_file) {
  maxR_win <- c(maxR1:maxR2);
  prdM <- env_mean_trait;
  kPara <- c();
  for (e_i in 1:nrow(env_mean_trait)) {
    envParas <- subset(PTT_PTR, PTT_PTR$env_code == env_mean_trait$env_code[e_i]);
    envPara <- mean(envParas[maxR_win, PTT_PTR_ind]);
    kPara[e_i] <- envPara;
  }
  prdM$kPara <- kPara;
  obs_prd_m <- matrix(0, ncol = 7,nrow = nrow(exp_trait));
  n1 <- 1; n2 <- 0;
  for (l in line_codes) {
    l_trait <- subset(exp_trait, exp_trait$line_code == l); 
    ril_data <- merge(prdM, l_trait,  all.x = T);
    trn <- ril_data[ril_data$env_code %in% trn_env, ];
    prd <- ril_data[!(ril_data$env_code %in% trn_env),];
     if (sum(!is.na(trn$Yobs)) >= 4 & sum(!is.na(prd$Yobs)) >= 1 ) {
 #   if (length(which(!is.na(ril_data$Yobs))) > 4) {
      obs_trait <- prd$Yobs;
      prd_trait_mean  <- round(predict( lm(Yobs ~ meanY, data = trn), prd), digit = 3);
      prd_trait_kpara <- round(predict( lm(Yobs ~ kPara, data = trn), prd), digit = 3);
      obs_prd_t <- cbind(prd$env_code, rep(p, nrow(prd)), rep(l, nrow(prd)), prd_trait_mean, prd_trait_kpara, prd$Yobs, rep(mean(trn$Yobs, na.rm = T), nrow(prd)));
      n2 <- n1 + nrow(prd) - 1;
      obs_prd_m[n1:n2,] <- obs_prd_t;
      n1 <- n2 + 1;
    }
  }
  obs_prd_m <- obs_prd_m[1:n2,]
  colnames(obs_prd_m) <- c('env_code', 'pop_code', 'ril_code', 'Prd_trait_mean', 'Prd_trait_kPara', 'Obs_trait', 'Line_mean');
  write.table(obs_prd_m, file = obs_prd_file, sep = "\t", quote = F, row.name = F);
  return(prdM);
}
################
LOOCV <- function(maxR1, maxR2, env_mean_trait, PTT_PTR, PTT_PTR_ind, exp_trait, obs_prd_file, p) {
 maxR_win <- c(maxR1:maxR2);
 prdM <- env_mean_trait;
 maxR_envPara <- matrix(ncol = 2, nrow = nrow(env_mean_trait));
 kPara <- c();
 for (e_i in 1:nrow(env_mean_trait)) {
   envParas <- subset(PTT_PTR, PTT_PTR$env_code == env_mean_trait$env_code[e_i]);
   envPara <- mean(envParas[maxR_win, PTT_PTR_ind]);
#   envPara <- mean(envParas$PTR[maxR_win]);
   kPara[e_i] <- envPara;
 }
 prdM$kPara <- kPara;
 obs_prd_m <- matrix(0, ncol = 7,nrow = nrow(exp_trait));
 
 n <- 0; 
 
 for (l in line_codes) {
   l_trait <- subset(exp_trait, exp_trait$line_code == l); 
   ril_data <- merge(prdM, l_trait,  all.x = T);
     if (length(which(!is.na(ril_data$Yobs))) > 4) {
     for (e in 1:nrow(ril_data)) {
       obs_trait <- ril_data$Yobs[e];
       if (!is.na(obs_trait)) {
         trn <- ril_data[-e,];
         l_mean <- mean(trn$Yobs, na.rm = T);
         prd_trait_mean  <- round(predict( lm(Yobs ~ meanY, data = trn), ril_data[e,]), digit = 3);
         prd_trait_kpara <- round(predict( lm(Yobs ~ kPara, data = trn), ril_data[e,]), digit = 3);
         n <- n + 1;
         obs_prd_m[n,] <- c(ril_data$env_code[e], p, l, prd_trait_mean, prd_trait_kpara, obs_trait, l_mean);
         
       }
     }
   }
 }
 
 obs_prd_m <- obs_prd_m[1:n,]
 colnames(obs_prd_m) <- c('env_code', 'pop_code', 'ril_code', 'Prd_trait_mean', 'Prd_trait_kPara', 'Obs_trait', 'Line_mean');
 write.table(obs_prd_m, file = obs_prd_file, sep = "\t", quote = F, row.name = F);
 return(prdM);
}

###################
Plot_prediction_result <- function(obs_prd_file, all_env_code, prdM, kPara_Name, forecast_png_file, env_cols) {
 Obs_Prd_m <- read.table(obs_prd_file, sep = "\t", header = T);
 Obs_Prd_m <- Obs_Prd_m[!is.na(Obs_Prd_m$Obs_trait),];
 prd_env <- as.vector(unique(Obs_Prd_m$env_code));
 env_rs <- matrix(ncol = 3, nrow = length(prd_env));
 for (e_i in 1:length(prd_env)) {
   env_obs_prd <- subset(Obs_Prd_m, Obs_Prd_m$env_code == prd_env[e_i]);
   if (nrow(env_obs_prd) > 0) {
    env_rs[e_i,] <- c( sprintf( "%.2f", cor(env_obs_prd[,4], env_obs_prd[,6], use = "complete.obs")), sprintf( "%.2f", cor(env_obs_prd[,5], env_obs_prd[,6], use = "complete.obs")), sprintf( "%.2f", cor(env_obs_prd[,7], env_obs_prd[,6], use = "complete.obs")));
   }
    
 }
 
 xy_lim <- range(Obs_Prd_m[,4:6],na.rm = T)
 
# pdf(forecast_pdf_file ,width = 4, height= 4,pointsize=6)
 png(forecast_png_file, width = 4/1.5, height= 4/1.5,pointsize=6, units = "in", res = 600)
 #
 #for (p in Pops) {
 layout(matrix(c(1:4), 2, 2, byrow = T));
 # screen(1)
  obs_prd_m <- subset(Obs_Prd_m, Obs_Prd_m$pop_code == p);
  par(mar = c(2.5, 2.5, 1.0, 0.5) , mgp = c(1, 0.25, 0), tck = -0.005, family = "mono");
  plot(obs_prd_m[,6], obs_prd_m[,4], col = env_cols[match(obs_prd_m[,1], all_env_codes)], pch = 19, cex = .4, ylab = paste('Predicted ', trait, ' by envMean', sep = ''), xlab = paste('Observed ', trait, '', sep = ''), xlim = xy_lim, ylim = xy_lim);
  abline(a = 0, b = 1, lty = 2, col = "gray59");
  r1 <- sprintf("%.2f", cor(obs_prd_m[,6], obs_prd_m[,4], use = "complete.obs"));
  legend("top", legend= substitute(paste(italic('r'), " = ", R1), list(R1 = r1)), bty = "n")
  LGs <- c()
  for (e in 1:length(prd_env)) {
    LGs <- append(LGs, bquote(.(E) * ' (' *italic(r) == .(A) * ')', list(E = prd_env[e], A = env_rs[e,1])))
  }
  legend("topleft", legend=do.call("expression", LGs), col = env_cols[match(prd_env, all_env_codes)],  pch = 19, cex = .65, bty = "n")
 
  mtext('A', side = 3, at = xy_lim[1], line = 0.1, cex = .8);
 # screen(2)
  par(mar = c(2.5, 2.5, 1.0, 0.5) , mgp = c(1, 0.25, 0), tck = -0.005, family = "mono");
  plot(obs_prd_m[,6], obs_prd_m[,5], col = env_cols[match(obs_prd_m[,1], all_env_codes)], pch = 19, cex = .4, ylab = paste('Predicted ', trait, ' by ', kPara_Name, sep = ''), xlab = paste('Observed ', trait, '', sep = ''), xlim = xy_lim, ylim = xy_lim);
  abline(a = 0, b = 1, lty = 2, col = "gray59");
  mtext('B', side = 3, at = xy_lim[1], line = 0.1, cex = .8);
  r2 <- sprintf("%.2f", cor(obs_prd_m[,6], obs_prd_m[,5], use = "complete.obs"));
  legend("top", legend= substitute(paste(italic('r'), " = ", R1), list(R1 = r2)), bty = "n")
  LGs <- c()
  for (e in 1:length(prd_env)) {
    LGs <- append(LGs, bquote(.(E) * ' (' *italic(r) == .(A) * ')', list(E = prd_env[e], A = env_rs[e,2])))
  }
  legend("topleft", legend=do.call("expression", LGs), col = env_cols[match(prd_env, all_env_codes)],  pch = 19, cex = .65, bty = "n")
 
  par(mar = c(2.5, 2.5, 1.0, 0.5) , mgp = c(1, 0.25, 0), tck = -0.005, family = "mono");
  plot(prdM$kPara, prdM$meanY, col = env_cols[match(prdM$env_code, all_env_codes)],  ylim = xy_lim, pch = 19, cex = .65, xlab = kPara_Name, ylab = 'Observed population mean');
  mtext(prdM$env_code, side = 1, at = prdM$kPara, las = 2, line = -2, cex = .6 )
  abline(lm(prdM$meanY ~ prdM$kPara))
   r2 <- sprintf("%.2f", cor(prdM$meanY, prdM$kPara));
  legend("top", legend= substitute(paste(italic('r'), " = ", R1), list(R1 = r2)), bty = "n")
 
  mtext('C', side = 3, at = min(prdM$kPara), line = 0.1, cex = .8);
 
 
 # screen(3)
  par(mar = c(2.5, 2.5, 1.0, 0.5) , mgp = c(1, 0.25, 0), tck = -0.005, family = "mono");
  plot(obs_prd_m[,6], obs_prd_m[,7], col = env_cols[match(obs_prd_m[,1], all_env_codes)], pch = 19, cex = .4, xlab = paste('Observed ', trait, sep = ''), ylab = paste('Predicted ', trait, ' by BLUE', sep = ''), xlim = xy_lim, ylim = xy_lim);
  abline(a = 0, b = 1, lty = 2, col = "gray59");
  r1 <- sprintf("%.2f", cor(obs_prd_m[,6], obs_prd_m[,7], use = "complete.obs"));
  legend("top", legend= substitute(paste(italic('r'), " = ", R1), list(R1 = r1)), bty = "n")
  LGs <- c()
  for (e in 1:length(prd_env)) {
    LGs <- append(LGs, bquote(.(E) * ' (' *italic(r) == .(A) * ')', list(E = prd_env[e], A = env_rs[e,3])))
  }
  legend("topleft", legend=do.call("expression", LGs), col = env_cols[match(prd_env, all_env_codes)],  pch = 19, cex = .65, bty = "n")
  mtext('D', side = 3, at = xy_lim[1], line = 0.1, cex = .8);
 dev.off()
}


#########
Pairwise_trait_env_distribution_plot <- function(exp_trait, exp_trait_dir, trait, all_env_codes, env_meta_info) {
 env_meta_info <- env_meta_info_0;
 env_mean_trait <- aggregate(x = exp_trait$Yobs, by = list(env_code = exp_trait$env_code), mean);
 n_envs <- nrow(env_mean_trait);
# trait_dist_pdf_file <- paste(exp_trait_dir, trait, '_dist_', n_envs, 'envs.pdf', sep = '');
 trait_dist_pdf_file <- paste(exp_trait_dir, trait, '_dist_', n_envs, 'envs.png', sep = '');
 pairwise_pdf_file <- paste(exp_trait_dir, trait, '_pairwise_dis', n_envs, 'envs.png', sep = '');
 mse_file <- paste(exp_trait_dir, n_envs, 'Env_meanY_MSE.txt', sep = '');

 colnames(env_mean_trait)[2] <- 'meanY';
 env_mean_trait <- env_mean_trait[order(env_mean_trait$meanY),];
 n_obs_env <- c(); quantile_1 <- c(); quantile_3 <- c(); key_para <- c(); key_para2 <- c();
 for (k in 1:nrow(env_mean_trait)) {
   env_data <- subset(exp_trait, exp_trait$env_code == env_mean_trait[k,1]);
   quantiles <- quantile(env_data$Yobs, na.rm = T);
   quantile_1[k] <- quantiles[2];
   quantile_3[k] <- quantiles[4];
   n_obs_env[k] <- length(which(!is.na(env_data$Yobs)))
 }
 env_mean_trait$q1 <- quantile_1; env_mean_trait$q3 <- quantile_3; env_mean_trait$n_obs <- n_obs_env;
 
 line_codes <- unique(as.vector(exp_trait$line_code)); 
 
 gray_alpha <- rgb(128, 128, 128, alpha = 35, maxColorValue = 255);
 poly_alpha <- rgb(238, 130, 238, alpha = 55.5, maxColorValue = 255);

 env_codes <- as.vector(env_mean_trait$env_code);
 line_by_env_df <- data.frame(line_code = line_codes);
 for (e_i in 1:nrow(env_mean_trait)) {
   e <- env_codes[e_i];
   e_trait <- subset(exp_trait, exp_trait$env_code == e);
   nonNAs <- length(which(!is.na(e_trait[,3])))
#   if (nonNAs > (0.5 * length(line_codes))) {
    colnames(e_trait)[3] <- e;
    line_by_env_df <- merge(line_by_env_df, e_trait[,c(1,3)], all.x = T)
#   }
 }
 write.table(line_by_env_df, file = paste(exp_trait_dir, 'LbE_table', n_envs, 'envs.txt', sep = ''), sep = "\t", row.names = F, quote = F);
 lm_residuals <- data.frame(env_code = env_mean_trait$env_code);
  for (l in line_codes) {
    line_trait_0 <- subset(exp_trait, exp_trait$line_code == l & !is.na(exp_trait$Yobs));
    if (nrow(line_trait_0) > 0) {
     line_trait_0 <-  merge(env_mean_trait, line_trait_0[,c(2,3)])
     line_lm <- lm(line_trait_0$Yobs ~ line_trait_0$meanY);
     df1 <- data.frame(env_code = line_trait_0$env_code, line_code = round((line_lm$residuals)^2, 3));
     colnames(df1)[2] <- l;
     lm_residuals <- merge(lm_residuals, df1, all.x = T)
    }
  }
  df2 <- data.frame(env_code = lm_residuals[,1], errors = rowMeans(lm_residuals[,-1], na.rm = T));
  df2 <- merge(df2, env_mean_trait);
  write.table(lm_residuals, file = mse_file, sep = "\t", row.names = F, quote = F);

 png(pairwise_pdf_file, width= 4 * 2,height= 3 * 2, unit = "in", res = 600, pointsize=10);
 corrgram(as.matrix(line_by_env_df[,-1]), order=TRUE, lower.panel=panel.ellipse, pch = 19, upper.panel=panel.pie);
 dev.off();
 
 png(trait_dist_pdf_file, width= 8,height= 2,pointsize=12, unit = "in", res = 600);

 layout(matrix(c(1:4), 1, 4, byrow = T))
 env_mean_trait <- env_mean_trait[env_mean_trait$env_code%in% colnames(line_by_env_df),]
 env_geo_order_df <- merge(env_mean_trait, env_meta_info);
 env_geo_order_df <- env_geo_order_df[order(env_geo_order_df$lat, env_geo_order_df$lon, env_geo_order_df$PlantingDate),];
 env_geo_order <- match(env_mean_trait$env_code, env_geo_order_df$env_code); ## 
 par(mar = c(5.0, 2.0, 1, 0.5) , mgp = c(1, 0.1, 0), tck = -0.01, cex.axis = .7, cex.lab = .8, family = "mono");
 plot(0, 0, col = "white", xlim = range(env_geo_order), ylim = range(exp_trait$Yobs, na.rm = T),  ylab = trait,  xlab = '', fg = "gray50", xaxt = "n");
 for (i in 1:nrow(line_by_env_df)) {
  df4 <- data.frame(env_code = env_mean_trait$env_code, env_order = env_geo_order, Yobs = as.numeric(line_by_env_df[i, -1]));
  df4 <- df4[!is.na(df4$Yobs),];
  df4 <- df4[order(df4$env_order),];
  points(df4$env_order, df4$Yobs, col = gray_alpha, type = "l", pch = 19, lwd = .6)
  points(df4$env_order, df4$Yobs, col = gray_alpha,  pch = 19, cex = .3)
 }
  points(c(1:nrow(env_geo_order_df)), env_geo_order_df$meanY, col = env_cols[match(as.vector(env_geo_order_df$env_code), all_env_codes )], cex = .8)
  points(c(1:nrow(env_geo_order_df)), env_geo_order_df$meanY, col = "black", type = "l", lwd = .5)

 mtext(env_geo_order_df$env_code, side = 1, at = c(1:nrow(env_geo_order_df)), las = 2, line = 0.5, cex = .6 )

 x_tick <- diff(env_mean_trait[,2]) / 50;
 par(mar = c(2.0, 2.0, 1, 0.5) , mgp = c(1, 0.1, 0), tck = -0.01, cex.axis = .7, family = "mono");
 plot(0, 0, col = "white", xlim = range(env_mean_trait$meanY), ylim = range(exp_trait$Yobs, na.rm = T), cex.lab = .9,  ylab = trait,  xlab = 'Population mean', fg = "gray50");
 for (i in 1:nrow(line_by_env_df)) {
   df3 <- data.frame(meanY = env_mean_trait$meanY, Yobs = as.numeric(line_by_env_df[i, -1]));
   df3 <- df3[!is.na(df3$Yobs),];
   points(df3$meanY, df3$Yobs, col = gray_alpha, type = "l", pch = 19, lwd = .3)
   points(df3$meanY, df3$Yobs, col = gray_alpha,  pch = 19, cex = .3)
 }
 abline(a = 0, b = 1, lty = 2, col = "grey")
  polygon(c(env_mean_trait[,2], rev(env_mean_trait[,2])), c( env_mean_trait$q1 , rev(env_mean_trait$q3)), col = poly_alpha, border = "NA")
 points(env_mean_trait$meanY, env_mean_trait$meanY, col = "black", cex = .4)
 legend("topleft", as.vector(env_mean_trait$env_code), col = env_cols[match(as.vector(env_mean_trait$env_code), all_env_codes )], pch = 19, bty = "n", cex = .8)
  
 for (k in 1:nrow(env_mean_trait)) {
   env_data <- subset(exp_trait, exp_trait$env_code == env_mean_trait[k,1]);
   boxplot(env_data$Yobs, add = T, boxwex = x_tick * 5 * 2, at = env_mean_trait$meanY[k], cex = .3, border = env_cols[match(as.vector(env_data$env_code), all_env_codes )], lwd = .4, boxlwd = .7, medlwd = .5, yaxt = "n")
 }
 ###
 par(mar = c(2.0, 2.0, 1, 0.5) , mgp = c(1, 0.1, 0), tck = -0.01, cex.axis = .7, family = "mono");
 plot(0, 0, col = "white", xlim = range(env_mean_trait$meanY), ylim = range(exp_trait$Yobs, na.rm = T), cex.lab = .9,  ylab = trait,  xlab = 'Population mean', fg = "gray50");
 for (i in 1:nrow(line_by_env_df)) {
   df3 <- data.frame(meanY = env_mean_trait$meanY, Yobs = as.numeric(line_by_env_df[i, -1]));
   df3 <- df3[!is.na(df3$Yobs),];
   if(nrow(df3) >= 4) {
    abline(lm(Yobs ~ meanY, data = df3), col = gray_alpha);
    points(df3$meanY, df3$Yobs, col = gray_alpha,  pch = 19, cex = .3)
   }
 }
 
 
 par(mar = c(4.0, 2.0, 1, 0.5) , mgp = c(0.75, 0.1, 0), tck = -0.01, cex.axis = .7, cex.lab = .8,  family = "mono");
 plot(df2$meanY, df2$errors, ylab = 'MSE', xlab = '', xaxt = "n", pch = 19, col = env_cols[match(as.vector(df2$env_code), all_env_codes )]);
 mtext(df2$env_code, side = 1, at = df2$meanY, las = 2, line = 0.5, cex = .6 )

 dev.off()
}

#################
Exhaustive_search <- function(env_mean_trait, env_paras, searching_daps, exp_trait_dir, FTdaps, trait, p, dap_x, dap_y, LOO, Paras, pop_cor_file) {
# env_paras <- PTT_PTR; FTdaps <- exp_traits$FTdap; p <- 1; dap_x <- searching_daps; dap_y <- searching_daps;

 exs_png_file <- paste(exp_trait_dir, 'MaxR_',trait, '_', nrow(env_mean_trait), 'Envs_', LOO, 'LOO.png', sep = ''); 
 
 nParas <- length(Paras);
 if (!file.exists(pop_cor_file)) {
  dap_win <- searching_daps * searching_daps  / 2;
      
    pop_cors_matrix <- matrix(ncol = 4 + (2 * nParas), nrow = dap_win * 1);
    colnames(pop_cors_matrix) <- c("pop_code", 'Day_x', 'Day_y', 'window', paste('R_', Paras, sep = ''), paste('nR_', Paras, sep = ''));
    n <- 0;
      for (d1 in 1:(dap_y - 6)) {
        for (d2 in (d1 + 6):dap_y) {
         days <- c(d1:d2); 
         env_facts_matrix <- matrix(nrow = nrow(env_mean_trait), ncol = nParas);
         for (e_i in 1:nrow(env_mean_trait)) {
           e <- env_mean_trait$env_code[e_i];
           env_para <- subset(env_paras, env_paras$env_code == e);
           env_mean <- colMeans(env_para[days, (1:nParas) + 2]); ### DL, GDD, DTR, PTT, PTR, PTD, PTD2, PTS
           env_facts_matrix[e_i,] <- env_mean;
         }
         n <- n + 1;
         ### leave one environment out and get the median correlation
         Ymean_envPara <- cbind(env_facts_matrix, env_mean_trait$meanY);
         rs <- c();
         if (LOO == 0) {
          for (k in 1:nParas) {
           rs[k] <- round(cor(Ymean_envPara[,nParas + 1], Ymean_envPara[,k]), digits = 4)
#           rs[k] <- round(-log(cor.test(Ymean_envPara[,8], Ymean_envPara[,k])$p.value, 10), digits = 4)
          }
         } else {
          loo_rs_matrix <- matrix(nrow = nrow(Ymean_envPara)+ 0, ncol = nParas);
          for (k in 1:nParas) { ## 8 environment parameters
           for (e_x in c(1:nrow(Ymean_envPara))) {
             t_matrix <- Ymean_envPara[-e_x,];
             loo_rs_matrix[e_x, k] <- round(cor(t_matrix[,nParas + 1], t_matrix[,k]), digits = 4)
            }
           }
          rs <- apply(loo_rs_matrix, 2, median);
         }
         pop_cors_matrix[n, ] <- c(p, d1, d2, d2 - d1, rs, 0 - rs);
        }
      }
    pop_cors_matrix <- pop_cors_matrix[1:n,]
    write.table(pop_cors_matrix, file = pop_cor_file, sep = "\t", row.names = F, quote = F);

 }

 pop_cors <- read.table(pop_cor_file, header = T, sep = "\t");
 pop_cor <- subset(pop_cors, pop_cors$pop_code == p);
# dev.off();
# pdf(exs_pdf_file,width= nParas,height= 2,pointsize=6)
 png(exs_png_file, width = nParas * 1.5, height = 2 * 1.5, pointsize = 12, unit = "in", res = 600)
 layout(matrix(c(1:(2*nParas)), 2, nParas, byrow = T))
 
 for (k in 1:(2*nParas)) {
   pop_cor_0 <- subset(pop_cors, pop_cors$pop_code == p); 
   pop_cor <- pop_cor_0[,c(1:4, k + 4)];
   colnames(pop_cor)[5] <- 'R';
   pop_cor <- pop_cor[order(pop_cor$R),];
   
   xs <- pop_cor$Day_x;  ys <-  pop_cor$Day_y;  mid_R <- median(pop_cor$R);
#   pop_cor_L <- subset(pop_cor, pop_cor$R <= mid_R); cor_range_L <- range(pop_cor_L$R);
#   cell_col_L <- floor((pop_cor_L$R - min(pop_cor_L$R)) / diff(cor_range_L) * col_wdw / 2) + 1;
#  
#   pop_cor_G <- subset(pop_cor, pop_cor$R > mid_R); cor_range_G <- range(pop_cor_G$R);
#   cell_col_G <- ceiling((pop_cor_G$R - min(pop_cor_G$R)) / diff(cor_range_G) * col_wdw / 2) + 12;
#   cell_col <- c(cell_col_L, cell_col_G);
    
   cell_col <- floor(pop_cor$R * 12) + 13; ### the same color scale
   
   pop_cor$cell_col <- cell_col; 
 
#   pop_cor_m <- subset(pop_cor, pop_cor$window > 4 & pop_cor$window < 50 ); ##& pop_cor$Day_x > (window_ref$dap_s - 10) & pop_cor$Day_y < (window_ref$dap_e + 10));
#   max_R <- pop_cor_m[which.max(pop_cor_m$R)[1], ];
   pop_cor_6 <- subset(pop_cor, pop_cor$window > 6); max_R <- pop_cor_6[which.max(pop_cor_6$R)[1], ];
   
   par(mar = c(0.5, 1.0, 1, 0.5) , mgp = c(0.05, 0.1, 0), tck = -0.01, bty = "n");
   plot(-50, -50, xlim = c(0, dap_x), ylim = c(0, dap_y), col = "white",  xlab = '', xaxt = "n", yaxt = "n", ylab = 'Days after planting', bty = "n", cex.lab = 1);
   arrows(-1, 10, -1, dap_y - 10, length = 0.05, angle = 15, lwd = .5,  col = "grey59");
   mtext(c(1, 50, 100, dap_y), side = 2, at = c(1,50, 100, dap_y), line = -1, cex = .6)
  
   rect(xs - 1, ys - 1, xs + 1, ys + 1, col = col_palette[pop_cor$cell_col], border = "NA")
   rect(max(pop_cor$Day_x) - 1, max(pop_cor$Day_y) - 1, max(pop_cor$Day_x) + 1, max(pop_cor$Day_y) + 1, border = "NA", col = "white", lwd = 0.01)
#   legend("bottom", Div_Fnd_lab, bty = "n", cex = .6);
  
#   arrows(10, dap_y + 4, dap_x - 10, dap_y + 4, angle = 15, length = 0.05, lwd = .5, col = "grey59")
#   mtext("Days after planting", side = 3, at = dap_x / 2, line = -0.1, cex = .4)
#   mtext(c(1, 50, 100, dap_y), side = 3, at = c(1, 50, 100, dap_y), line = -1.1, cex = .6)
#   arrows(max_R$Day_x + 4,  max_R$Day_y - 4,  max_R$Day_x,  max_R$Day_y, length = 0.05, angle = 15, lwd = .5, col = "grey59")
   
   box_ys <- seq(1, 50, by = 2); box_xs <- rep(dap_x - 15, 25); 
   rect(box_xs - 1 * 2, box_ys - 1 * 2, box_xs + 1 * 2, box_ys + 1 * 2, border = "NA", col = col_palette)
   text(dap_x - 10 - 5, 52, 'r', cex = .5);
   r_lab_top <- 1; r_lab_mid <- 0; r_lab_bottom <- -1; max_r_lab <- paste( 'r = ', sprintf( "%.3f", max_R$R), sep = '');
   if (k > nParas) { r_lab_top <- -1; r_lab_bottom <- 1; max_r_lab <- paste( 'r = ', sprintf( "%.3f", 0 - max_R$R), sep = ''); mtext(side = 1, Paras[k - nParas ], line= -0.5,  cex = .5, bty = "n")}
#  legend(max_R$Day_x - 4 , max_R$Day_y - 4 , c(paste( max_R$Day_x, ' to ', max_R$Day_y, ' DAP', sep = ''), max_r_lab),  cex = .6, bty = "n");
   text(dap_x - 10 + 3, 50, r_lab_top, cex = .5)
   text(dap_x - 10 + 3, 27, r_lab_mid, cex = .5);
   text(dap_x - 10 + 3, 1,  r_lab_bottom, cex = .5)
   if (length(FTdaps) > 1) {
    boxplot(FTdaps,   at = 145,  add = TRUE, xaxt = "n", yaxt = "n", xlab = '', ylab = '', width = 10, pch = 19, cex = 1, boxwex = 4, lwd = .4, col = "gold", border = "grey");
    boxplot(FTdaps,   at = 1, horizontal = T, add = TRUE, xaxt = "n", yaxt = "n", xlab = '', ylab = '', width = 10, pch = 19, cex = .3, boxwex = 4, lwd = .4, col = "gold", border = "grey");
    text(mean(FTdaps), 5, 'Days to anthesis', cex = .5)
    text(mean(FTdaps), 10, paste('Trait: ', trait, sep = ''), cex = 1)
    }
 }
 dev.off()
 

}

##### 
#####
Plot_Trait_mean_envParas <- function( env_mean_trait, env_paras, d1, d2, trait, exp_trait_dir, env_cols, Paras){
  nParas <- length(Paras);
  days <- c(d1:d2); 
  env_facts_matrix <- matrix(nrow = nrow(env_mean_trait), ncol = nParas + 1);
  for (e_i in 1:nrow(env_mean_trait)) {
    e <- env_mean_trait$env_code[e_i];
    env_para <- subset(env_paras, env_paras$env_code == e);
    env_mean <- colMeans(env_para[days, (1:nParas) + 2]); ### DL, GDD, PTT, PTR, PTS
    
    env_facts_matrix[e_i,] <- c(env_mean_trait$meanY[e_i], round(env_mean, 4) );
  }
  colnames(env_facts_matrix) <- c( 'meanY', Paras);
  envMeanPara_file <- paste(exp_trait_dir, trait, '_envMeanPara_', d1, '_', d2, '.txt', sep = '');
  envMeanPara <- merge(env_mean_trait, env_facts_matrix);
  write.table(envMeanPara, file = envMeanPara_file, sep = "\t", row.names = F, quote = F);
#  trait_mean_envPara <- merge(env_mean_trait, env_facts_matrix, stringsAsFactors = F);
  
  png_file <- paste(exp_trait_dir, trait, 'Mean_', nrow(env_mean_trait), 'EnvPara.png', sep = ''); 
  png(png_file,width= nParas * 2,height= 2 * 1,pointsize= 12, unit = "in", res = 600)

  layout(matrix(c(1:nParas), nrow = 1, byrow = T));
  
  for (i in 1:nParas) {
   par(mar = c(2.5, 2.0, 1, 0.5) , mgp = c(0.7, 0.01, 0), tck = -0.01, family = "mono");
   plot(env_facts_matrix[, i + 1], env_facts_matrix[,1], xlab = colnames(env_paras)[i + 4], ylab = paste(trait, ' mean', sep = ''),  pch = 19, col = env_cols);
   abline(lm(env_facts_matrix[,1] ~ env_facts_matrix[, i + 1]), lty = 2);
   r1 <- round(cor(env_facts_matrix[,1] , env_facts_matrix[, i + 1]), 3);
   legend("bottom", paste('r = ', r1, sep = ''), bty = "n")
   legend_p <- "topleft";  if (r1 < 0) { legend_p <- "topright"};
   if (i == 1) { legend(legend_p, env_mean_trait$env_code, pch = 19, col = env_cols, bty = "n" )};
  }
  dev.off()
}

####### regression each line to the ennvironmental mean and parameter

Slope_Intercept <- function(maxR_dap1, maxR_dap2, env_mean_trait, PTT_PTR, exp_trait, line_codes, exp_trait_dir) {
 maxR_win <- c(maxR_dap1:maxR_dap2);
 prdM <- env_mean_trait;
 kPara <- c();
 for (e_i in 1:nrow(env_mean_trait)) {
   envParas <- subset(PTT_PTR, PTT_PTR$env_code == env_mean_trait$env_code[e_i]);
   envPara <- mean(envParas[maxR_win, PTT_PTR_ind]);
#   envPara <- mean(envParas$PTR[maxR_win]);
   kPara[e_i] <- envPara;
 }
 prdM$kPara <- kPara;
 lm_ab_matrix <- matrix(ncol = 5, nrow = length(line_codes));
 for (l in 1: length(line_codes)) {
   l_trait <- subset(exp_trait, exp_trait$line_code == line_codes[l]);
   if(nrow(l_trait) >= 5) {
     l_trait <- merge(l_trait, prdM);
     lm_Mean <- lm(Yobs ~ meanY, data = l_trait);
     lm_Para <- lm(Yobs ~ kPara, data = l_trait); 
     a_Mean <- as.vector(round(predict(lm_Mean, data.frame(meanY = mean(prdM$meanY))), 4)); ## adjusted by the population mean
     b_Mean <- as.vector(round(lm_Mean$coefficient[2], 4));
     b_Para <- as.vector(round(lm_Para$coefficient[2],4));
     a_Para <- as.vector(round(predict(lm_Para, data.frame(kPara = mean(prdM$kPara))), 4)); ## adjusted by the population mean
     a_Para_ori <- as.vector(round(lm_Para$coefficient[1],4));
     lm_ab_matrix[l,] <- c(line_codes[l], a_Mean, b_Mean, a_Para, b_Para);
   }
 }
 lm_ab_matrix <- lm_ab_matrix[!is.na(lm_ab_matrix[,2]),];
 colnames(lm_ab_matrix) <- c('line_code', 'Intcp_mean', 'Slope_mean',  'Intcp_para', 'Slope_para');
 out_file <- paste(exp_trait_dir, 'Intcp_Slope', nrow(env_mean_trait), 'envs.txt', sep = '');
 write.table(lm_ab_matrix, file = out_file, sep = "\t", quote = F, row.names = F)

} 

######## From Tingting Guo ######
JGRA=function(LOC,pheno,geno,envir,enp,tt.line,tt.e,mets,fold=10,reshuffle=50)
{
  
  colnames(pheno)=as.character(unlist(pheno[1,]));
  envir.name=colnames(pheno)[-1];
  
  pheno=pheno[-1,];
  m=pheno[,-1];
  m=as.numeric(as.character(unlist(m)));m <- matrix(data=m, ncol=dim(pheno)[2]-1, nrow=dim(pheno)[1]);
  colnames(m)=colnames(pheno)[-1];
  pheno_=data.frame(line_code=pheno$line_code,m);
  colnames(pheno_)=c("line_code",envir.name);
  pheno=pheno_;
  
  envir=envir[envir$env_code%in%envir.name,];
  LOC=LOC[LOC$env_code%in%envir.name,];
  
  order=match(envir$env_code,LOC$env_code);
  LOC=LOC[order,];
  #pheno=pheno[,as.character(envir$env_code)];
  
  rm.env=colnames(pheno)[colSums(is.na(pheno))>=tt.line];
  LOC=LOC[which(!(LOC$env_code%in%rm.env)),];
  envir=envir[which(!(envir$env_code%in%rm.env)),];
  pheno=pheno[,which(!(colnames(pheno)%in%rm.env))];
  
  pheno.1=pheno
  keep=dim(pheno.1)[2]-rowSums(is.na(pheno.1))
  pheno=pheno.1[which(keep>=tt.e),];
  n.line=dim(pheno)[1];
  n.envir=dim(pheno)[2]-1;
  
  #library("yarrr")
  #coloo=piratepal(palette="basel",trans=0)[1:n.envir];
  coloo=heat.colors(n.envir);
  
  if(mets=="RM.E") 
  {
    pheno.hat=matrix(999,n.line,dim(envir)[1]);
    cor.whole=numeric();
    for(k in 1:n.envir)
    {
      for(j in 1:n.line)
      {
        x1=envir[,enp][-k];
        y1=as.vector(t(pheno[j,-c(1,1+k)]));
        
        coe=lm(y~x,data=data.frame(x=x1,y=y1));
        y.hat=summary(coe)$coefficients[1,1]+summary(coe)$coefficients[2,1]*envir[,enp][k];
        pheno.hat[j,k]=y.hat;
      }
      cor.each=cor(pheno.hat[,k],pheno[,k+1], use = "complete.obs");
      cor.whole=c(cor.whole,cor.each);
    }
    observe=as.vector(as.matrix(pheno[,-1]));
    predict=as.vector(pheno.hat);

    r_within=cor.whole;names(r_within)=colnames(pheno)[-1];
    r_within=data.frame(cor_within=r_within,envir=colnames(pheno)[-1]);
    r_across=cor(observe,predict,use = "complete.obs");
    outforfigure=data.frame(obs=observe,pre=predict,col=rep(coloo,times=rep(n.line,n.envir)),envir=rep(colnames(pheno)[-1],times=rep(n.line,n.envir)))
  }
  
  if(mets=="RM.G") 
  {
    intercept=numeric();
    slope=numeric();
    for(j in 1:n.line)
    {
      x1=envir[,enp];
      y1=as.vector(t(pheno[j,-c(1)]));
      
      coe=lm(y~x,data=data.frame(x=x1,y=y1));
      inter=summary(coe)$coefficients[1,1]
      slop=summary(coe)$coefficients[2,1];
      intercept=c(intercept,inter);
      slope=c(slope,slop);
    }
    
    genotype.match=match(pheno[,1],geno[,1])
    #genotype=geno[genotype.match,];
    genotype_1=geno[genotype.match,];
    genotype.impute=A.mat(genotype_1[,-1],max.missing=0.5,impute.method="mean",return.imputed=T);
    SFI=cbind(genotype_1[,1],genotype.impute$imputed);
    genotype=matrix(suppressWarnings(as.numeric(SFI)),nrow=nrow(SFI))
    Marker=genotype[,-1];
    
    intercept.hat=numeric();slope.hat=numeric();cor.within=matrix(999,reshuffle,n.envir);cor.all=numeric();
    for(i in 1:reshuffle)
    { 

#      cross=sample(rep(1:fold,each=round(n.line/fold,0)),n.line);
      cross = sample(rep(1:fold,each=ceiling(n.line/fold)),n.line)
      yhat.whole.cross=numeric();yobs.whole.cross=numeric();
      for(f in 1:fold)
      {
        id.T=c(1:n.line)[cross!=f]; id.V=c(1:n.line)[cross==f];
        ##Intercept###
        y0=intercept; 
        ans<-mixed.solve(y=y0[id.T],Z=genotype[id.T,-1])
        e=as.matrix(ans$u)
        G.pred=Marker[id.V,]
        y_pred=as.matrix(G.pred) %*% e
        GEBV.inter=c(y_pred[,1])+c(ans$beta);
        ##Slope###
        y0=slope; 
        ans<-mixed.solve(y=y0[id.T],Z=genotype[id.T,-1])
        e=as.matrix(ans$u)
        G.pred=Marker[id.V,]
        y_pred=as.matrix(G.pred) %*% e
        GEBV.slope=c(y_pred[,1])+c(ans$beta);
        ###All the predicted slope and intercept
        yhat.envir=matrix(999,length(id.V),n.envir);yobs.envir=matrix(999,length(id.V),n.envir)
        for(j in 1:n.envir)
        {
          yhat=GEBV.inter+GEBV.slope*envir[j,enp];
          yobs=pheno[id.V,j+1];
          yhat.envir[,j]=yhat;yobs.envir[,j]=yobs;
        }
        yhat.whole.cross=rbind(yhat.whole.cross,yhat.envir);
        yobs.whole.cross=rbind(yobs.whole.cross,yobs.envir);
      }
       for(j in 1:n.envir)
       {cor.within[i,j]=cor(yhat.whole.cross[,j],yobs.whole.cross[,j],use = "complete.obs");}
      
      cor.all=c(cor.all,cor(as.vector(yhat.whole.cross),as.vector(yobs.whole.cross),use = "complete.obs"));
    }
    #Correlation within environment 50 times
    r_within=apply(cor.within,2,mean);names(r_within)=colnames(pheno)[-1];
    r_within=data.frame(cor_within=r_within,envir=colnames(pheno)[-1]);
    #Correlation across environment 50 times
    r_across=mean(cor.all);
    #Observation and prediction last time
    outforfigure=data.frame(obs=as.vector(yobs.whole.cross),
                            pre=as.vector(yhat.whole.cross),
                            col=rep(coloo,times=rep(n.line,n.envir)),envir=rep(colnames(pheno)[-1],times=rep(n.line,n.envir)))
    colnames(cor.within)=colnames(pheno)[-1];
    r_within=cor.within;
    r_across=cor.all;
  }   
  
  if(mets=="RM.GE") 
  { 
    genotype.match=match(pheno[,1],geno[,1])
    genotype_1=geno[genotype.match,];
    genotype.impute=A.mat(genotype_1[,-1],max.missing=0.5,impute.method="mean",return.imputed=T);
    SFI=cbind(genotype_1[,1],genotype.impute$imputed);
    genotype=matrix(suppressWarnings(as.numeric(SFI)),nrow=nrow(SFI))
    Marker=genotype[,-1];
    
    cor.within=matrix(999,reshuffle,n.envir);cor.all=numeric();
    for(i in 1:reshuffle)
    {
      obs_matrix=matrix(999,n.line,n.envir);pre_matrix=matrix(999,n.line,n.envir);
      for(k in 1:n.envir)
      {
        intercept=numeric();
        slope=numeric();
        for(j in 1:n.line)
        {
          x1=envir[-k,enp];
          y1=as.vector(t(pheno[j,-c(1,1+k)]));
          
          coe=lm(y~x,data=data.frame(x=x1,y=y1));
          inter=summary(coe)$coefficients[1,1]
          slop=summary(coe)$coefficients[2,1];
          intercept=c(intercept,inter);
          slope=c(slope,slop);
        }
        
        cross = sample(rep(1:fold,each=ceiling(n.line/fold)),n.line)
        yhat.whole=numeric();yobs.whole=numeric();
        
        for(f in 1:fold)
        {
          id.T=c(1:n.line)[cross!=f]; id.V=c(1:n.line)[cross==f];
          ##Intercept###
          y0=intercept; 
          ans<-mixed.solve(y=y0[id.T],Z=genotype[id.T,-1])
          e=as.matrix(ans$u)
          G.pred=Marker[id.V,]
          y_pred=as.matrix(G.pred) %*% e
          GEBV.inter=c(y_pred[,1])+c(ans$beta);
          ##Slope###
          y0=slope; 
          ans<-mixed.solve(y=y0[id.T],Z=genotype[id.T,-1])
          e=as.matrix(ans$u)
          G.pred=Marker[id.V,]
          y_pred=as.matrix(G.pred) %*% e
          GEBV.slope=c(y_pred[,1])+c(ans$beta);
          ###All the predicted slope and intercept
          yhat=GEBV.inter+GEBV.slope*envir[k,enp];
          yobs=pheno[id.V,k+1];
          
          yhat.whole=c(yhat.whole,yhat);
          yobs.whole=c(yobs.whole,yobs);
        }
        cor.within[i,k]=cor(yhat.whole,yobs.whole,use = "complete.obs");
        obs_matrix[,k]=yobs.whole;
        pre_matrix[,k]=yhat.whole;
      }
      cor.shuffle=cor(as.vector(obs_matrix),as.vector(pre_matrix),use = "complete.obs")
      cor.all=c(cor.all,cor.shuffle);
    }
     
    yhat.whole.cross=pre_matrix;
    yobs.whole.cross=obs_matrix;
    #Correlation within environment 50 times
    r_within=apply(cor.within,2,mean);names(r_within)=colnames(pheno)[-1];
    #Correlation across environment 50 times
    r_across=mean(cor.all);
    #Observation and prediction last time
    outforfigure=data.frame(obs=as.vector(yobs.whole.cross),
                            pre=as.vector(yhat.whole.cross),
                            col=rep(coloo,times=rep(n.line,n.envir)),envir=rep(colnames(pheno)[-1],times=rep(n.line,n.envir)))
    colnames(cor.within)=colnames(pheno)[-1];
    r_within=cor.within;
    r_across=cor.all;
    
  }
  
  return(list(outforfigure,r_within,r_across));
}
JGRA.marker=function(LOC,pheno,geno,envir,enp,tt.line,tt.e,mets,fold=10,reshuffle=50)
{
colnames(pheno)=as.character(unlist(pheno[1,]));
envir.name=colnames(pheno)[-1];

pheno=pheno[-1,];
m=pheno[,-1];
m=as.numeric(as.character(unlist(m)));m <- matrix(data=m, ncol=dim(pheno)[2]-1, nrow=dim(pheno)[1]);
colnames(m)=colnames(pheno)[-1];
pheno_=data.frame(line_code=pheno$line_code,m);
colnames(pheno_)=c("line_code",envir.name);
pheno=pheno_;

envir=envir[envir$env_code%in%envir.name,];
LOC=LOC[LOC$env_code%in%envir.name,];

order=match(envir$env_code,LOC$env_code);
LOC=LOC[order,];
#pheno=pheno[,as.character(envir$env_code)];

rm.env=colnames(pheno)[colSums(is.na(pheno))>=tt.line];
LOC=LOC[which(!(LOC$env_code%in%rm.env)),];
envir=envir[which(!(envir$env_code%in%rm.env)),];
pheno=pheno[,which(!(colnames(pheno)%in%rm.env))];

pheno.1=pheno
keep=dim(pheno.1)[2]-rowSums(is.na(pheno.1))
pheno=pheno.1[which(keep>=tt.e),];
n.line=dim(pheno)[1];
n.envir=dim(pheno)[2]-1;

#library("yarrr")
#coloo=piratepal(palette="basel",trans=0)[1:n.envir];
coloo=heat.colors(n.envir);

genotype.match=match(pheno[,1],geno[,1])
#genotype=geno[genotype.match,];
    genotype_1=geno[genotype.match,];
    genotype.impute=A.mat(genotype_1[,-1],max.missing=0.5,impute.method="mean",return.imputed=T);
    SFI=cbind(genotype_1[,1],genotype.impute$imputed);
    genotype=matrix(suppressWarnings(as.numeric(SFI)),nrow=nrow(SFI))

Marker=genotype[,-1];
n.marker=dim(Marker)[2];

if(mets=="RM.E") 
{
 
  effect=matrix(999,n.marker,n.envir);
  intercept=matrix(999,1,n.envir)
  
  for(i in 1:n.envir)
  {
    fit=mixed.solve(pheno[,1+i],Z=Marker)
    effect[,i]=fit$u
    intercept[,i]=fit$beta
  }
  
  pheno.hat=matrix(999,n.line,dim(envir)[1]);
  cor.whole=numeric();
  for(k in 1:n.envir)
  {
    
    effect.hat=numeric();
    for(j in 1:n.marker)
    {
      x1=envir[,enp][-k];
      y1=effect[j,-k];
      
      coe=lm(y~x,data=data.frame(x=x1,y=y1));
      y.hat=summary(coe)$coefficients[1,1]+summary(coe)$coefficients[2,1]*envir[,enp][k];
      effect.hat=c(effect.hat,y.hat);
    }
    
    ##Environment intercept####
    reg.intercept=data.frame(x=as.numeric(envir[,enp][-k]),y=as.vector(intercept[-k]));
    coe.intercept=lm(y~x,data=reg.intercept)
    y.intercept=summary(coe.intercept)$coefficients[1,1]+summary(coe.intercept)$coefficients[2,1]*as.numeric(envir[,enp][k]);
    
    pheno.hat[,k]=y.intercept+as.matrix(Marker)%*%as.matrix(effect.hat);
    cor.each=cor(pheno.hat[,k],pheno[,k+1], use = "complete.obs");
    cor.whole=c(cor.whole,cor.each);
  }
  observe=as.vector(as.matrix(pheno[,-1]));
  predict=as.vector(pheno.hat);
  r_within=cor.whole;names(r_within)=colnames(pheno)[-1];
  r_within=data.frame(cor_within=r_within,envir=colnames(pheno)[-1]);
  r_across=cor(observe,predict,use = "complete.obs");
  outforfigure=data.frame(obs=observe,pre=predict,col=rep(coloo,times=rep(n.line,n.envir)),envir=rep(colnames(pheno)[-1],times=rep(n.line,n.envir)))
}

if(mets=="RM.G") 
{
  cor.within=matrix(999,reshuffle,n.envir);cor.all=numeric();
  for(i in 1:reshuffle)
  {
    cross = sample(rep(1:fold,each=ceiling(n.line/fold)),n.line)
    yhat.whole.cross=numeric();yobs.whole.cross=numeric();
    for(f in 1:fold)
    {
      id.T=c(1:n.line)[cross!=f]; id.V=c(1:n.line)[cross==f];
      ##marker effect###
      effect=matrix(999,n.marker,n.envir);
      intercept=matrix(999,1,n.envir)
    
      for(k in 1:n.envir)
      {
      fit=mixed.solve(pheno[id.T,1+k],Z=Marker[id.T,])
      effect[,k]=fit$u
      intercept[,k]=fit$beta
      }
    
      ##Slope###
      effect.hat=numeric();
      for(j in 1:n.marker)
      {
        x1=envir[,enp];
        y1=effect[j,];
        coe=lm(y~x,data=data.frame(x=x1,y=y1));
        y.hat=summary(coe)$coefficients[1,1]+summary(coe)$coefficients[2,1]*envir[,enp];
        effect.hat=rbind(effect.hat,y.hat);
      }
      
      ##Environment intercept####
      reg.intercept=data.frame(x=as.numeric(envir[,enp]),y=as.vector(intercept));
      coe.intercept=lm(y~x,data=reg.intercept)
      y.intercept=summary(coe.intercept)$coefficients[1,1]+summary(coe.intercept)$coefficients[2,1]*as.numeric(envir[,enp]);
    
      ###All the predicted slope and intercept
      yhat.envir=matrix(999,length(id.V),n.envir);yobs.envir=matrix(999,length(id.V),n.envir)
      for(j in 1:n.envir)
      {
      yhat=y.intercept[j]+(as.matrix(Marker[id.V,])%*%as.matrix(effect.hat))[,j];
      yobs=pheno[id.V,j+1];
      yhat.envir[,j]=yhat;yobs.envir[,j]=yobs;
      }
      yhat.whole.cross=rbind(yhat.whole.cross,yhat.envir);
      yobs.whole.cross=rbind(yobs.whole.cross,yobs.envir);
    }
    
    for(j in 1:n.envir)
    {cor.within[i,j]=cor(yhat.whole.cross[,j],yobs.whole.cross[,j],use = "complete.obs");}
    cor.all=c(cor.all,cor(as.vector(yhat.whole.cross),as.vector(yobs.whole.cross),use = "complete.obs"));
  }
  #Correlation within environment 50 times
  r_within=apply(cor.within,2,mean);names(r_within)=colnames(pheno)[-1];
  #Correlation across environment 50 times
  r_across=mean(cor.all);
  #Observation and prediction last time
  outforfigure=data.frame(obs=as.vector(yobs.whole.cross),
                          pre=as.vector(yhat.whole.cross),
                          col=rep(coloo,times=rep(n.line,n.envir)),envir=rep(colnames(pheno)[-1],times=rep(n.line,n.envir)))
  colnames(cor.within)=colnames(pheno)[-1];
  r_within=cor.within;
  r_across=cor.all;
}   

if(mets=="RM.GE") 
{ 
  cor.within=matrix(999,reshuffle,n.envir);cor.all=numeric();
  for(i in 1:reshuffle)
  {
    cross = sample(rep(1:fold,each=ceiling(n.line/fold)),n.line)
    obs_matrix=numeric();pre_matrix=numeric();
    for(f in 1:fold)
    {
      id.T=c(1:n.line)[cross!=f]; id.V=c(1:n.line)[cross==f];
      ##marker effect###
      effect=matrix(999,n.marker,n.envir);
      intercept=matrix(999,1,n.envir)
      
      for(k in 1:n.envir)
      {
        fit=mixed.solve(pheno[id.T,1+k],Z=Marker[id.T,])
        effect[,k]=fit$u
        intercept[,k]=fit$beta
      }
      
      ##predict marker effect###
      obs.envir=numeric();pre.envir=numeric();
      for(kk in 1:n.envir)
      {
        effect.hat=numeric();
        for(j in 1:n.marker)
        {
          x1=envir[-kk,enp];
          y1=effect[j,-kk];
          coe=lm(y~x,data=data.frame(x=x1,y=y1));
          y.hat=summary(coe)$coefficients[1,1]+summary(coe)$coefficients[2,1]*envir[kk,enp];
          effect.hat=rbind(effect.hat,y.hat);
        }
        ##Environment intercept####
        reg.intercept=data.frame(x=as.numeric(envir[-kk,enp]),y=as.vector(intercept[-kk]));
        coe.intercept=lm(y~x,data=reg.intercept)
        y.intercept=summary(coe.intercept)$coefficients[1,1]+summary(coe.intercept)$coefficients[2,1]*as.numeric(envir[kk,enp]);
      
      ###All the predicted slope and intercept
        yhat=y.intercept+(as.matrix(Marker[id.V,])%*%as.matrix(effect.hat));
        yobs=pheno[id.V,kk+1];
        obs.envir=cbind(obs.envir,yobs);
        pre.envir=cbind(pre.envir,yhat);
      }
      obs_matrix=rbind(obs_matrix,obs.envir);pre_matrix=rbind(pre_matrix,pre.envir);
      
    }
    cor.shuffle=cor(as.vector(obs_matrix),as.vector(pre_matrix),use = "complete.obs")
    cor.all=c(cor.all,cor.shuffle);
    for(j in 1:n.envir)
    {cor.within[i,j]=cor(obs_matrix[,j],pre_matrix[,j],use = "complete.obs");}
  } 
    
  yhat.whole.cross=pre_matrix;
  yobs.whole.cross=obs_matrix;
  #Correlation within environment 50 times
  r_within=apply(cor.within,2,mean);names(r_within)=colnames(pheno)[-1];
  #Correlation across environment 50 times
  r_across=mean(cor.all);
  #Observation and prediction last time
  outforfigure=data.frame(obs=as.vector(yobs.whole.cross),
                          pre=as.vector(yhat.whole.cross),
                          col=rep(coloo,times=rep(n.line,n.envir)),envir=rep(colnames(pheno)[-1],times=rep(n.line,n.envir)))
  colnames(cor.within)=colnames(pheno)[-1];
  r_within=cor.within;
  r_across=cor.all;
  
}   

return(list(outforfigure,r_within,r_across));
}
