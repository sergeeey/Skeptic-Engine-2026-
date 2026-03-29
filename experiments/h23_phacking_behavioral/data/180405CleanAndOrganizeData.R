################################################################
### Statistical reporting inconsistencies: meta-analyses
### 4-5-2018
### Clean data
################################################################

# clear workspace
rm(list=ls())

# load packages
library(tidyverse)

################################################################
################### DATA CLEANING ##############################
################################################################

# set working directory to location of the data
setwd("C:/Users/mnuijten/surfdrive/UVT/Projects/CampbellGrant/statcheckDataMetaAnalyses/1. RunStatcheck")

# load raw data
data <- read.csv2("180405statcheckDataMetaAnalyses.csv", header = TRUE)

#--------------------------------------------------------------------

# add years to raw data
# by extracting the year published from the file name

# add to data
years <- NULL
for(i in 1:nrow(data)){
  yrLoc <- gregexpr("\\(\\d{4}\\)",data$Source[i])[[1]]
  foo <- try(substring(data$Source[i],yrLoc+1,yrLoc+attr(yrLoc,"match.length")-2))
  if(!is(class(foo),"try-error")){
    years[i] <- foo
  } else {
    years[i] <- NA
  }
}

data$year <- years

#--------------------------------------------------------------------

# organize data  on article level
data_per_article <- data %>%
  group_by(Source) %>%
  summarize(year = unique(year),
            nr_NHST = n(),
            errors = sum(Error, na.rm=TRUE),
            dec_errors = sum(DecisionError, na.rm=TRUE),
            perc_errors = round(errors/nr_NHST*100,2),
            perc_dec_errors = round(dec_errors/nr_NHST*100,2),
            folder = unique(folder))

setwd("C:/Users/mnuijten/surfdrive/UVT/Projects/CampbellGrant/statcheckDataMetaAnalyses/2. CleanData")
write.table(data_per_article, "data_per_article.txt", sep = "\t", row.names = FALSE)

